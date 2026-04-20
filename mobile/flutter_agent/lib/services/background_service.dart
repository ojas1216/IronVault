import 'dart:async';
import 'dart:ui';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_background_service_android/flutter_background_service_android.dart';
import '../services/heartbeat_service.dart';
import '../services/location_service.dart';
import '../services/app_usage_service.dart';

class BackgroundService {
  static Future<void> startForegroundService() async {
    final service = FlutterBackgroundService();

    await service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: onStart,
        autoStart: true,
        isForegroundMode: true,
        notificationChannelId: 'mdm_service',
        initialNotificationTitle: 'Company Device Security',
        initialNotificationContent: 'Protecting your device',
        foregroundServiceNotificationId: 888,
      ),
      iosConfiguration: IosConfiguration(
        autoStart: true,
        onForeground: onStart,
        onBackground: onIosBackground,
      ),
    );

    await service.startService();
  }

  @pragma('vm:entry-point')
  static Future<bool> onIosBackground(ServiceInstance service) async {
    return true;
  }

  @pragma('vm:entry-point')
  static void onStart(ServiceInstance service) async {
    DartPluginRegistrant.ensureInitialized();

    if (service is AndroidServiceInstance) {
      service.on('setAsForeground').listen((_) {
        service.setAsForegroundService();
      });
    }

    HeartbeatService.start();

    // Location update every 5 minutes
    Timer.periodic(const Duration(minutes: 5), (_) {
      LocationService.sendLocationUpdate();
    });

    // App usage sync every hour
    Timer.periodic(const Duration(hours: 1), (_) {
      AppUsageService.syncUsage();
    });

    service.on('stopService').listen((_) {
      service.stopSelf();
    });
  }
}

class BackgroundTaskRunner {
  static Future<void> runTask(String task, Map<String, dynamic>? inputData) async {
    switch (task) {
      case 'heartbeatTask':
        await HeartbeatService.sendHeartbeat();
        break;
    }
  }
}
