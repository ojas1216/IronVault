import UIKit
import Flutter
import UserNotifications

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {

    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        GeneratedPluginRegistrant.register(with: self)

        // Request push notification permission for APNs commands
        requestNotificationPermission()

        // Set up Flutter method channel for native iOS MDM calls
        setupMDMChannel()

        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }

    // ─── APNs Registration ────────────────────────────────────────────────────

    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .badge, .sound]
        ) { granted, error in
            if granted {
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        }
    }

    override func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        // Convert token to hex string
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()

        // Send to Flutter layer via method channel
        if let controller = window?.rootViewController as? FlutterViewController {
            let channel = FlutterMethodChannel(
                name: "com.company.mdmagent/apns",
                binaryMessenger: controller.binaryMessenger
            )
            channel.invokeMethod("onTokenReceived", arguments: tokenString)
        }
    }

    override func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        print("[MDM] APNs registration failed: \(error.localizedDescription)")
    }

    // Handle foreground push (command received)
    override func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        let userInfo = notification.request.content.userInfo
        handleMDMCommand(userInfo: userInfo)
        // Don't show banner for silent MDM commands
        let isSilent = userInfo["mdm_command"] != nil
        completionHandler(isSilent ? [] : [.banner, .sound])
    }

    // Handle background push
    override func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        handleMDMCommand(userInfo: userInfo)
        completionHandler(.newData)
    }

    // ─── MDM Command Handling ─────────────────────────────────────────────────

    private func handleMDMCommand(userInfo: [AnyHashable: Any]) {
        guard let command = userInfo["mdm_command"] as? String else { return }

        if let controller = window?.rootViewController as? FlutterViewController {
            let channel = FlutterMethodChannel(
                name: "com.company.mdmagent/commands",
                binaryMessenger: controller.binaryMessenger
            )
            channel.invokeMethod("executeCommand", arguments: [
                "command": command,
                "payload": userInfo["payload"] ?? [:],
                "command_id": userInfo["command_id"] ?? "",
                "pre_verified": userInfo["pre_verified"] ?? "false",
            ])
        }
    }

    // ─── Native MDM Channel Setup ────────────────────────────────────────────

    private func setupMDMChannel() {
        guard let controller = window?.rootViewController as? FlutterViewController else { return }

        let channel = FlutterMethodChannel(
            name: "com.company.mdmagent/native",
            binaryMessenger: controller.binaryMessenger
        )

        channel.setMethodCallHandler { [weak self] call, result in
            switch call.method {
            case "lockDevice":
                self?.lockDevice(result: result)
            case "getDeviceInfo":
                self?.getDeviceInfo(result: result)
            case "isSupervised":
                result(false) // Supervised mode requires Apple Business Manager
            default:
                result(FlutterMethodNotImplemented)
            }
        }
    }

    private func lockDevice(result: FlutterResult) {
        // On iOS without supervision, can only show lock screen guidance
        // Full lock requires MDM enrollment via Apple Business Manager + DEP
        let alert = UIAlertController(
            title: "Device Locked",
            message: "This device has been locked by your IT administrator.",
            preferredStyle: .alert
        )
        window?.rootViewController?.present(alert, animated: true)
        result(true)
    }

    private func getDeviceInfo(result: FlutterResult) {
        let info: [String: Any] = [
            "model": UIDevice.current.model,
            "system_version": UIDevice.current.systemVersion,
            "identifier_for_vendor": UIDevice.current.identifierForVendor?.uuidString ?? "",
            "name": UIDevice.current.name,
        ]
        result(info)
    }
}
