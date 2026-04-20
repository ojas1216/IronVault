import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import '../services/api_service.dart';

/// UWB (Ultra-Wideband) Tracking Service — Precision Location Layer
///
/// Android 12+ with UWB chip: ±10–30 cm accuracy (Pixel 6+, Samsung S21+)
/// iOS iPhone 11+: NearbyInteraction framework (±10 cm)
/// Fallback (no UWB chip): BLE RSSI ranging (~1–3 m accuracy)
class UWBService {
  static const _channel = MethodChannel('com.company.mdmagent/uwb');
  static const _eventChannel = EventChannel('com.company.mdmagent/uwb_ranging');

  static StreamSubscription? _rangingSub;
  static final _rangingController = StreamController<UWBRangingResult>.broadcast();

  /// Live ranging results stream
  static Stream<UWBRangingResult> get rangingStream => _rangingController.stream;

  static Future<bool> isSupported() async {
    try {
      return await _channel.invokeMethod<bool>('isUwbSupported') ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Start ranging to target device
  static Future<String> startRanging({
    required String targetDeviceId,
    List<int>? peerUwbAddress,
  }) async {
    final result = await _channel.invokeMethod<Map>('startRanging', {
      'peer_address': peerUwbAddress,
      'session_id': targetDeviceId.hashCode.abs(),
    });

    final mode = result?['mode'] as String? ?? 'unknown';

    _rangingSub?.cancel();
    _rangingSub = _eventChannel.receiveBroadcastStream().listen((event) {
      final data = Map<String, dynamic>.from(event as Map);
      _rangingController.add(UWBRangingResult.fromMap(data));
      _syncRangingToBackend(targetDeviceId, data);
    });

    return mode; // 'uwb' or 'ble_fallback'
  }

  static Future<void> stopRanging() async {
    _rangingSub?.cancel();
    await _channel.invokeMethod('stopRanging');
  }

  static Future<void> _syncRangingToBackend(
      String deviceId, Map<String, dynamic> data) async {
    try {
      await ApiService.post('/uwb/ranging', {
        'device_id': deviceId,
        'distance_meters': data['distance_meters'],
        'azimuth_degrees': data['azimuth_degrees'],
        'elevation_degrees': data['elevation_degrees'],
        'mode': data['mode'],
        'timestamp': DateTime.now().toIso8601String(),
      });
    } catch (_) {}
  }

  /// iOS NearbyInteraction setup
  static Future<void> setupIosNearbyInteraction(String peerToken) async {
    if (!Platform.isIOS) return;
    const iosChannel = MethodChannel('com.company.mdmagent/nearby_ios');
    await iosChannel.invokeMethod('startSession', {'peer_token': peerToken});
  }
}

class UWBRangingResult {
  final String mode; // 'uwb' | 'ble_fallback' | 'ios_nearby'
  final double distanceMeters;
  final double? azimuthDegrees;  // horizontal direction
  final double? elevationDegrees; // vertical angle
  final int? rssi;
  final DateTime timestamp;

  const UWBRangingResult({
    required this.mode,
    required this.distanceMeters,
    this.azimuthDegrees,
    this.elevationDegrees,
    this.rssi,
    required this.timestamp,
  });

  factory UWBRangingResult.fromMap(Map<String, dynamic> map) {
    return UWBRangingResult(
      mode: map['mode'] as String? ?? 'unknown',
      distanceMeters: (map['distance_meters'] as num?)?.toDouble() ?? 0.0,
      azimuthDegrees: (map['azimuth_degrees'] as num?)?.toDouble(),
      elevationDegrees: (map['elevation_degrees'] as num?)?.toDouble(),
      rssi: map['rssi'] as int?,
      timestamp: DateTime.now(),
    );
  }

  /// Human-readable direction instruction
  String get directionHint {
    if (azimuthDegrees == null) return 'Searching...';
    final a = azimuthDegrees!;
    if (distanceMeters < 0.3) return 'Right here! (${(distanceMeters * 100).toInt()} cm)';
    if (distanceMeters < 1.0) return 'Very close — ${(distanceMeters * 100).toInt()} cm';
    final dir = _azimuthToDirection(a);
    return '$dir — ${distanceMeters.toStringAsFixed(1)} m';
  }

  static String _azimuthToDirection(double degrees) {
    if (degrees >= -22.5 && degrees < 22.5) return 'Straight ahead ↑';
    if (degrees >= 22.5 && degrees < 67.5) return 'Turn right 45° ↗';
    if (degrees >= 67.5 && degrees < 112.5) return 'Turn right →';
    if (degrees >= 112.5 && degrees < 157.5) return 'Turn right 135° ↘';
    if (degrees >= 157.5 || degrees < -157.5) return 'Turn around ↓';
    if (degrees >= -157.5 && degrees < -112.5) return 'Turn left 135° ↙';
    if (degrees >= -112.5 && degrees < -67.5) return 'Turn left ←';
    if (degrees >= -67.5 && degrees < -22.5) return 'Turn left 45° ↖';
    return 'Searching...';
  }
}
