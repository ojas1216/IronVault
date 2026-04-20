import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:workmanager/workmanager.dart';

import 'config/app_config.dart';
import 'services/enrollment_service.dart';
import 'services/background_service.dart';
import 'services/fcm_service.dart';
import 'screens/enrollment_screen.dart';
import 'screens/status_screen.dart';
import 'utils/secure_storage.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await FCMService.handleBackgroundMessage(message);
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    await BackgroundTaskRunner.runTask(task, inputData);
    return Future.value(true);
  });
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  await Workmanager().initialize(callbackDispatcher, isInDebugMode: false);

  // Register periodic background sync (every 15 minutes — minimum allowed)
  await Workmanager().registerPeriodicTask(
    "mdm-heartbeat",
    "heartbeatTask",
    frequency: const Duration(minutes: 15),
    constraints: Constraints(networkType: NetworkType.connected),
  );

  runApp(const ProviderScope(child: MDMAgentApp()));
}

class MDMAgentApp extends ConsumerWidget {
  const MDMAgentApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Company Device Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1565C0)),
        useMaterial3: true,
      ),
      home: const AppEntryPoint(),
    );
  }
}

class AppEntryPoint extends ConsumerStatefulWidget {
  const AppEntryPoint({super.key});

  @override
  ConsumerState<AppEntryPoint> createState() => _AppEntryPointState();
}

class _AppEntryPointState extends ConsumerState<AppEntryPoint> {
  bool _isEnrolled = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _checkEnrollment();
  }

  Future<void> _checkEnrollment() async {
    final token = await SecureStorage.getDeviceToken();
    setState(() {
      _isEnrolled = token != null;
      _isLoading = false;
    });

    if (_isEnrolled) {
      await FCMService.initialize();
      await BackgroundService.startForegroundService();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return _isEnrolled ? const StatusScreen() : const EnrollmentScreen();
  }
}
