import 'dart:async';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../utils/secure_storage.dart';

/// Section 6 — Uninstall & Tamper Resistance
class TamperMonitor {
  static const _channel = MethodChannel('com.company.mdmagent/tamper');

  /// 6.4 — Block airplane mode (Device Owner only)
  static Future<void> blockAirplaneMode() async {
    await _channel.invokeMethod('blockAirplaneMode');
  }

  /// Re-enable airplane mode control (for authorized removal)
  static Future<void> unblockAirplaneMode() async {
    await _channel.invokeMethod('unblockAirplaneMode');
  }

  /// 6.5 — Start anti-force-stop watchdog
  static void startWatchdog() {
    _channel.invokeMethod('startWatchdog');
  }

  /// 6.3 — Lock power menu (Device Owner — hides power-off option)
  static Future<void> lockPowerMenu() async {
    await _channel.invokeMethod('lockPowerMenu');
  }

  /// Log tamper attempt to backend
  static Future<void> reportTamper(String type, String details) async {
    final deviceId = await SecureStorage.getDeviceId();
    if (deviceId == null) return;
    try {
      await ApiService.post('/devices/tamper-event', {
        'device_id': deviceId,
        'tamper_type': type,
        'details': details,
        'timestamp': DateTime.now().toIso8601String(),
      });
    } catch (_) {}
  }

  /// 6.1 — Validate PIN entered by employee before allowing admin revoke
  static Future<bool> validateAdminPin(String pin) async {
    try {
      final result = await _channel.invokeMethod<bool>('validatePin', {'pin': pin});
      return result ?? false;
    } catch (_) {
      return false;
    }
  }
}
