import 'dart:io';
import 'package:app_usage/app_usage.dart';
import '../services/api_service.dart';

class AppUsageService {
  static Future<void> syncUsage() async {
    if (!Platform.isAndroid) return; // app usage API is Android-only

    try {
      final now = DateTime.now();
      final from = now.subtract(const Duration(hours: 1));

      final usage = await AppUsage().getAppUsage(from, now);

      if (usage.isEmpty) return;

      final logs = usage
          .where((u) => u.usage.inSeconds > 0)
          .map((u) => {
                'app_package': u.packageName,
                'app_name': u.appName,
                'usage_duration_seconds': u.usage.inSeconds,
                'is_work_app': false,
                'date': now.toIso8601String(),
              })
          .toList();

      await ApiService.post('/devices/app-usage', {'logs': logs});
    } catch (_) {}
  }
}
