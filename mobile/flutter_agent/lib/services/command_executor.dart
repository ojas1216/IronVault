import 'dart:async';
import 'dart:io';
import '../services/api_service.dart';
import '../services/alarm_service.dart';
import '../services/camera_service.dart';
import '../services/location_service.dart';
import '../services/sim_service.dart';
import '../services/device_identity_service.dart';
import '../services/tamper_monitor.dart';
import '../utils/secure_storage.dart';
import 'package:flutter/services.dart';

/// Executes MDM commands received from backend via FCM/APNs.
/// Destructive commands (uninstall, wipe) require OTP verification.
class CommandExecutor {
  static const _dpmChannel = MethodChannel('com.company.mdmagent/dpm');
  static const _uninstallChannel = MethodChannel('com.company.mdmagent/uninstall');

  // Stream for uninstall OTP dialog trigger
  static final _uninstallStream =
      StreamController<Map<String, String>>.broadcast();
  static Stream<Map<String, String>> get onUninstallRequest =>
      _uninstallStream.stream;

  static String? _pendingCommandId;
  static String? _pendingOtpId;

  static Future<void> execute({
    required String commandType,
    required String commandId,
    required Map<String, dynamic> payload,
  }) async {
    try {
      switch (commandType) {

        // ── Section 7.2 Core Actions ──────────────────────────────────────
        case 'lock_device':
          await _lockDevice(commandId);

        case 'trigger_alarm':
          final duration = payload['duration_seconds'] as int? ?? 30;
          await AlarmService.triggerAlarm(durationSeconds: duration);
          await _report(commandId, 'completed');

        case 'stop_alarm':
          await AlarmService.stopAlarm();
          await _report(commandId, 'completed');

        case 'location_request':
          await LocationService.sendLocationUpdate();
          await _report(commandId, 'completed');

        case 'capture_front_camera':
          await _captureFrontCamera(commandId);

        case 'extract_sim_metadata':
          await _extractAndReportSim(commandId);

        case 'extract_device_identity':
          await _extractAndReportIdentity(commandId);

        case 'remote_uninstall':
          await _handleUninstall(commandId, payload);

        case 'wipe_device':
          await _wipeDevice(commandId);

        case 'reboot':
          await _dpmChannel.invokeMethod('reboot');
          await _report(commandId, 'completed');

        case 'enable_lost_mode':
          await _dpmChannel.invokeMethod('enableLostMode', payload);
          await _report(commandId, 'completed');

        case 'disable_lost_mode':
          await _dpmChannel.invokeMethod('disableLostMode');
          await _report(commandId, 'completed');

        case 'block_airplane_mode':
          await TamperMonitor.blockAirplaneMode();
          await _report(commandId, 'completed');

        case 'policy_update':
          await _applyPolicy(commandId, payload);

        default:
          await _report(commandId, 'failed',
              error: 'Unknown command: $commandType');
      }
    } catch (e) {
      await _report(commandId, 'failed', error: e.toString());
    }
  }

  static Future<void> _lockDevice(String commandId) async {
    if (Platform.isAndroid) {
      await _dpmChannel.invokeMethod('lockDevice');
    }
    await _report(commandId, 'completed');
  }

  static Future<void> _captureFrontCamera(String commandId) async {
    final photoPath = await CameraService.captureSecurityPhoto(
      trigger: 'remote_command',
    );
    if (photoPath != null) {
      await CameraService.uploadPhoto(photoPath, commandId);
      await _report(commandId, 'completed',
          result: {'photo_captured': true});
    } else {
      await _report(commandId, 'failed', error: 'Camera capture failed');
    }
  }

  static Future<void> _extractAndReportSim(String commandId) async {
    final metadata = await SimService.extractSimMetadata();
    await _report(commandId, 'completed', result: {'sim_metadata': metadata});
  }

  static Future<void> _extractAndReportIdentity(String commandId) async {
    final identity = await DeviceIdentityService.buildIdentityPayload();
    await _report(commandId, 'completed',
        result: {'device_identity': identity});
  }

  static Future<void> _handleUninstall(
      String commandId, Map<String, dynamic> payload) async {
    final otpId = payload['otp_id'] as String?;
    if (otpId == null) {
      await _report(commandId, 'failed', error: 'Missing OTP ID');
      return;
    }
    _pendingCommandId = commandId;
    _pendingOtpId = otpId;
    _uninstallStream.add({'command_id': commandId, 'otp_id': otpId});
  }

  static Future<void> executeVerifiedUninstall(
      String commandId, String otpId, String otpCode) async {
    final deviceId = await SecureStorage.getDeviceId();
    final response = await ApiService.post('/commands/verify-otp', {
      'otp_id': otpId,
      'otp_code': otpCode,
      'device_id': deviceId,
    });

    if (response.data['verified'] == true) {
      if (Platform.isAndroid) {
        await _uninstallChannel.invokeMethod('requestUninstall');
      }
      await _report(commandId, 'completed');
    } else {
      await _report(commandId, 'failed', error: 'OTP verification failed');
    }
  }

  static Future<void> _wipeDevice(String commandId) async {
    if (Platform.isAndroid) {
      await _dpmChannel.invokeMethod('wipeDevice');
    }
    await _report(commandId, 'completed');
  }

  static Future<void> _applyPolicy(
      String commandId, Map<String, dynamic> payload) async {
    // Apply policy settings from payload
    final blockAirplane = payload['block_airplane_mode'] as bool? ?? false;
    if (blockAirplane) await TamperMonitor.blockAirplaneMode();
    await _report(commandId, 'completed');
  }

  static Future<void> _report(String commandId, String status,
      {String? error, Map<String, dynamic>? result}) async {
    try {
      await ApiService.post('/devices/command-result', {
        'command_id': commandId,
        'status': status,
        if (error != null) 'error_message': error,
        if (result != null) 'result': result,
      });
    } catch (_) {}
  }
}

