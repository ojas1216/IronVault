import 'dart:async';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../services/camera_service.dart';
import '../services/location_service.dart';

/// SIM Intelligence Layer — Section 5 of requirements.
/// Extracts SIM metadata, monitors SIM lifecycle, and reports anomalies.
/// Only operates on company-enrolled devices with disclosed policy.
class SimService {
  static const _channel = MethodChannel('com.company.mdmagent/sim');
  static const _eventChannel = EventChannel('com.company.mdmagent/sim_events');

  static StreamSubscription? _simEventSubscription;

  /// 5.1 — Extract full SIM metadata payload
  static Future<Map<String, dynamic>> extractSimMetadata() async {
    try {
      final result = await _channel.invokeMethod<Map>('getSimMetadata');
      return Map<String, dynamic>.from(result ?? {});
    } catch (e) {
      return {'error': e.toString()};
    }
  }

  /// 5.2 — Start SIM lifecycle monitoring (insert / remove / swap)
  static void startMonitoring() {
    _simEventSubscription?.cancel();
    _simEventSubscription = _eventChannel
        .receiveBroadcastStream()
        .listen((event) => _handleSimEvent(Map<String, dynamic>.from(event)));
  }

  static void stopMonitoring() => _simEventSubscription?.cancel();

  /// 5.3 — SIM anomaly response pipeline
  static Future<void> _handleSimEvent(Map<String, dynamic> event) async {
    final eventType = event['event_type'] as String?; // inserted|removed|swapped
    final slotIndex = event['slot_index'] as int? ?? 0;

    // 1. Auto-trigger location ping
    await LocationService.sendLocationUpdate();

    // 2. Auto-trigger front camera capture (security photo)
    final photoPath = await CameraService.captureSecurityPhoto(
      trigger: 'sim_$eventType',
    );

    // 3. Extract current SIM state
    final simMetadata = await extractSimMetadata();

    // 4. Auto-create incident log on backend
    await ApiService.post('/sim-events/report', {
      'event_type': eventType,
      'slot_index': slotIndex,
      'sim_metadata': simMetadata,
      'photo_path': photoPath,
      'timestamp': DateTime.utc(
        DateTime.now().year, DateTime.now().month, DateTime.now().day,
        DateTime.now().hour, DateTime.now().minute, DateTime.now().second,
      ).toIso8601String(),
    });
  }
}
