import 'dart:io';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../services/api_service.dart';
import '../services/device_identity_service.dart';
import '../utils/secure_storage.dart';
import '../config/app_config.dart';

class EnrollmentService {
  static Future<EnrollmentResult> enrollDevice({
    required String employeeName,
    required String employeeEmail,
    required String employeeId,
    required String department,
    required String pushToken,
  }) async {
    final deviceInfo = DeviceInfoPlugin();
    final packageInfo = await PackageInfo.fromPlatform();

    String deviceName = '';
    String platform = '';
    String model = '';
    String osVersion = '';

    if (Platform.isAndroid) {
      final info = await deviceInfo.androidInfo;
      deviceName = info.model;
      platform = 'android';
      model = '${info.manufacturer} ${info.model}';
      osVersion = 'Android ${info.version.release}';
    } else if (Platform.isIOS) {
      final info = await deviceInfo.iosInfo;
      deviceName = info.name;
      platform = 'ios';
      model = info.model;
      osVersion = 'iOS ${info.systemVersion}';
    }

    // Collect full hardware identity for anti-resale golden fingerprint
    Map<String, dynamic> hardwareIdentity = {};
    try {
      hardwareIdentity = await DeviceIdentityService.buildIdentityPayload();
    } catch (_) {}

    try {
      final response = await ApiService.post('/devices/enroll', {
        'device_name': deviceName,
        'employee_name': employeeName,
        'employee_email': employeeEmail,
        'employee_id': employeeId,
        'department': department,
        'platform': platform,
        'device_model': model,
        'os_version': osVersion,
        'push_token': pushToken,
        'agent_version': packageInfo.version,
        'enrollment_code': AppConfig.enrollmentCode,
        // Hardware identity — establishes the golden fingerprint for anti-resale tracking
        if (hardwareIdentity['android_id'] != null)
          'android_id': hardwareIdentity['android_id'],
        if (hardwareIdentity['serial_number'] != null)
          'serial_number': hardwareIdentity['serial_number'],
        if (hardwareIdentity['hardware_fingerprint'] != null)
          'hardware_fingerprint': hardwareIdentity['hardware_fingerprint'],
        if (hardwareIdentity['imei_slot1'] != null)
          'imei1': hardwareIdentity['imei_slot1'],
        if (hardwareIdentity['imei_slot2'] != null)
          'imei2': hardwareIdentity['imei_slot2'],
      });

      final data = response.data as Map<String, dynamic>;
      await SecureStorage.saveDeviceToken(data['device_token']);
      await SecureStorage.saveDeviceId(data['device_id']);
      await SecureStorage.saveEnrollmentToken(data['enrollment_token']);

      // Warn if resale was detected for this hardware
      final warning = data['warning'];
      return EnrollmentResult(
        success: true,
        deviceId: data['device_id'],
        resaleWarning: warning == 'RESALE_DETECTED',
      );
    } catch (e) {
      return EnrollmentResult(success: false, error: e.toString());
    }
  }
}

class EnrollmentResult {
  final bool success;
  final String? deviceId;
  final String? error;
  final bool resaleWarning;

  const EnrollmentResult({
    required this.success,
    this.deviceId,
    this.error,
    this.resaleWarning = false,
  });
}
