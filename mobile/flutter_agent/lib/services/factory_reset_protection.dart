import 'package:flutter/services.dart';

/// Factory Reset Protection Service
///
/// Ensures that after a factory reset, the company's MDM agent is
/// automatically reinstalled via Android Enterprise Zero-touch enrollment.
///
/// Methods use the Device Owner FRP API (Android 11+).
class FactoryResetProtectionService {
  static const _channel = MethodChannel('com.company.mdmagent/frp');

  /// Enable FRP — after any factory reset, device requires company Google account
  static Future<bool> enable({String companyAccount = 'it-admin@yourcompany.com'}) async {
    try {
      final result = await _channel.invokeMethod<bool>('enableFactoryResetProtection', {
        'company_account': companyAccount,
      });
      return result ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Prevent users from triggering factory reset via Settings
  static Future<bool> blockFactoryReset() async {
    try {
      return await _channel.invokeMethod<bool>('blockFactoryReset') ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Block safe mode boot (prevents policy bypass)
  static Future<bool> blockSafeMode() async {
    try {
      return await _channel.invokeMethod<bool>('blockSafeMode') ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Block USB debugging (prevents ADB uninstall bypass)
  static Future<bool> blockUsbDebugging() async {
    try {
      return await _channel.invokeMethod<bool>('blockUsbDebugging') ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Apply all protections at once — call during enrollment
  static Future<void> applyAllProtections() async {
    await blockFactoryReset();
    await blockSafeMode();
    await blockUsbDebugging();
    await enable();
  }
}
