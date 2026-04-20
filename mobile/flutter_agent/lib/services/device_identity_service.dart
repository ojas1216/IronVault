import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:crypto/crypto.dart';
import 'package:device_info_plus/device_info_plus.dart';

/// Section 4 — IMEI & Device Identity Layer
class DeviceIdentityService {
  static const _channel = MethodChannel('com.company.mdmagent/identity');

  /// IMEI read (Device Owner scope on Android 10+)
  static Future<String?> getImei({int slotIndex = 0}) async {
    try {
      return await _channel.invokeMethod<String>('getImei', {'slot': slotIndex});
    } catch (_) {
      return null;
    }
  }

  /// Device serial (requires Device Owner on Android 10+)
  static Future<String?> getSerial() async {
    try {
      return await _channel.invokeMethod<String>('getSerial');
    } catch (_) {
      final info = await DeviceInfoPlugin().androidInfo;
      return info.id;
    }
  }

  /// Android ID (stable per device + app signing key)
  static Future<String?> getAndroidId() async {
    try {
      return await _channel.invokeMethod<String>('getAndroidId');
    } catch (_) {
      return null;
    }
  }

  /// WiFi MAC address from sysfs (persistent, not subject to randomisation)
  static Future<String?> getWifiMac() async {
    try {
      return await _channel.invokeMethod<String>('getWifiMac');
    } catch (_) {
      return null;
    }
  }

  /// Bluetooth MAC address
  static Future<String?> getBluetoothMac() async {
    try {
      return await _channel.invokeMethod<String>('getBluetoothMac');
    } catch (_) {
      return null;
    }
  }

  /// SoC manufacturer and model (Android 12+)
  static Future<Map<String, String?>> getSocInfo() async {
    try {
      final result = await _channel.invokeMapMethod<String, String?>('getSocInfo');
      return result ?? {};
    } catch (_) {
      return {};
    }
  }

  /// Standard hardware fingerprint — SHA-256 of board/brand/device/hardware/manufacturer/model/product
  static Future<String> buildHardwareFingerprint() async {
    final info = await DeviceInfoPlugin().androidInfo;
    final components = [
      info.board,
      info.brand,
      info.device,
      info.hardware,
      info.manufacturer,
      info.model,
      info.product,
    ].join('|');
    return sha256.convert(utf8.encode(components)).toString();
  }

  /// Extended hardware fingerprint — includes SoC, WiFi MAC, BT MAC, serial.
  /// Any hardware component swap will change this fingerprint.
  static Future<String> buildExtendedFingerprint() async {
    try {
      final result = await _channel.invokeMethod<String>('getExtendedFingerprint');
      if (result != null && result.isNotEmpty) return result;
    } catch (_) {}
    return buildHardwareFingerprint();
  }

  /// Firmware fingerprint — SHA-256 of build fingerprint + bootloader + security patch.
  /// Detects firmware updates, tampered bootloaders, and OS manipulation.
  static Future<String?> getFirmwareFingerprint() async {
    try {
      return await _channel.invokeMethod<String>('getFirmwareFingerprint');
    } catch (_) {
      return null;
    }
  }

  /// Full identity payload for enrollment / backend sync
  static Future<Map<String, dynamic>> buildIdentityPayload() async {
    final info = await DeviceInfoPlugin().androidInfo;
    final imei = await getImei();
    final imei2 = await getImei(slotIndex: 1);
    final serial = await getSerial();
    final androidId = await getAndroidId();
    final wifiMac = await getWifiMac();
    final btMac = await getBluetoothMac();
    final soc = await getSocInfo();
    final fingerprint = await buildExtendedFingerprint();
    final firmwareFingerprint = await getFirmwareFingerprint();

    return {
      'imei_slot1': imei,
      'imei_slot2': imei2,
      'serial_number': serial,
      'android_id': androidId,
      'wifi_mac': wifiMac,
      'bt_mac': btMac,
      'soc_manufacturer': soc['soc_manufacturer'],
      'soc_model': soc['soc_model'],
      'hardware_fingerprint': fingerprint,
      'firmware_fingerprint': firmwareFingerprint,
      'board': info.board,
      'brand': info.brand,
      'device': info.device,
      'hardware': info.hardware,
      'manufacturer': info.manufacturer,
      'model': info.model,
      'os_version': 'Android ${info.version.release}',
      'sdk_int': info.version.sdkInt,
    };
  }
}
