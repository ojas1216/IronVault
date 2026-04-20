import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  static const _keyDeviceToken = 'device_token';
  static const _keyDeviceId = 'device_id';
  static const _keyEnrollmentToken = 'enrollment_token';

  static Future<void> saveDeviceToken(String token) =>
      _storage.write(key: _keyDeviceToken, value: token);

  static Future<String?> getDeviceToken() =>
      _storage.read(key: _keyDeviceToken);

  static Future<void> saveDeviceId(String id) =>
      _storage.write(key: _keyDeviceId, value: id);

  static Future<String?> getDeviceId() =>
      _storage.read(key: _keyDeviceId);

  static Future<void> saveEnrollmentToken(String token) =>
      _storage.write(key: _keyEnrollmentToken, value: token);

  static Future<String?> getEnrollmentToken() =>
      _storage.read(key: _keyEnrollmentToken);

  static Future<void> clearAll() => _storage.deleteAll();
}
