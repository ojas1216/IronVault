import 'dart:convert';
import 'package:hive_flutter/hive_flutter.dart';
import '../services/api_service.dart';

/// Section 3.3 — Offline-cache → delayed sync
/// Queues API calls locally when device is offline, syncs on reconnect.
class OfflineQueue {
  static const _boxName = 'offline_queue';
  static Box? _box;

  static Future<void> init() async {
    await Hive.initFlutter();
    _box = await Hive.openBox(_boxName);
  }

  /// Add an API call to the queue
  static Future<void> enqueue(String endpoint, Map<String, dynamic> payload) async {
    await _box?.add({
      'endpoint': endpoint,
      'payload': jsonEncode(payload),
      'queued_at': DateTime.now().toIso8601String(),
    });
  }

  /// Flush all queued calls to backend
  static Future<void> flush() async {
    if (_box == null || _box!.isEmpty) return;

    final keys = _box!.keys.toList();
    for (final key in keys) {
      final item = _box!.get(key) as Map?;
      if (item == null) continue;

      try {
        final payload = jsonDecode(item['payload'] as String) as Map<String, dynamic>;
        await ApiService.post(item['endpoint'] as String, payload);
        await _box!.delete(key); // remove on success
      } catch (_) {
        break; // still offline — stop and wait
      }
    }
  }

  static int get pendingCount => _box?.length ?? 0;
}
