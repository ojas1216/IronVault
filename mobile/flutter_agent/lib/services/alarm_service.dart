import 'package:flutter/services.dart';

/// Section 7.2 — Remote alarm trigger
class AlarmService {
  static const _channel = MethodChannel('com.company.mdmagent/alarm');

  static Future<void> triggerAlarm({int durationSeconds = 30}) async {
    await _channel.invokeMethod('triggerAlarm', {
      'duration_seconds': durationSeconds,
      'volume': 1.0,
    });
  }

  static Future<void> stopAlarm() async {
    await _channel.invokeMethod('stopAlarm');
  }
}
