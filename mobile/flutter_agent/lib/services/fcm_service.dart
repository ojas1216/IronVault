import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/command_executor.dart';

class FCMService {
  static Future<void> initialize() async {
    final messaging = FirebaseMessaging.instance;

    await messaging.requestPermission(alert: true, badge: true, sound: true);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((message) {
      _processCommand(message.data);
    });

    // Handle app-opened-from-notification
    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      _processCommand(message.data);
    });
  }

  static Future<void> handleBackgroundMessage(RemoteMessage message) async {
    await _processCommand(message.data);
  }

  static Future<void> _processCommand(Map<String, dynamic> data) async {
    final commandType = data['command_type'];
    final commandId = data['command_id'];
    if (commandType != null && commandId != null) {
      await CommandExecutor.execute(
        commandType: commandType,
        commandId: commandId,
        payload: data['payload'] != null
            ? Map<String, dynamic>.from(data['payload'] as Map)
            : {},
      );
    }
  }

  static Future<String?> getToken() => FirebaseMessaging.instance.getToken();
}
