import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../services/device_identity_service.dart';
import '../config/app_config.dart';

class HeartbeatService {
  static const _tamperChannel = MethodChannel('com.company.mdmagent/tamper');
  static Timer? _timer;

  static void start() {
    _timer?.cancel();
    _timer = Timer.periodic(
      const Duration(seconds: AppConfig.heartbeatInterval),
      (_) => sendHeartbeat(),
    );
    sendHeartbeat();
  }

  static void stop() => _timer?.cancel();

  static Future<void> sendHeartbeat() async {
    try {
      final connectivity = await Connectivity().checkConnectivity();
      final networkType = connectivity.isNotEmpty ? connectivity.first.name : 'unknown';

      bool isRooted = false;
      try {
        final result = await _tamperChannel.invokeMethod('checkTamper');
        isRooted = result['is_rooted'] ?? false;
      } catch (_) {}

      // Hardware fingerprint — sent every heartbeat for continuous resale/tamper detection
      String? hardwareFingerprint;
      String? firmwareFingerprint;
      try {
        hardwareFingerprint = await DeviceIdentityService.buildExtendedFingerprint();
        firmwareFingerprint = await DeviceIdentityService.getFirmwareFingerprint();
      } catch (_) {}

      await ApiService.post('/devices/heartbeat', {
        'is_rooted': isRooted,
        'network_type': networkType,
        if (hardwareFingerprint != null) 'hardware_fingerprint': hardwareFingerprint,
        if (firmwareFingerprint != null) 'firmware_fingerprint': firmwareFingerprint,
      });
    } catch (_) {
      // Offline — commands will sync via polling when back online
    }
  }
}
