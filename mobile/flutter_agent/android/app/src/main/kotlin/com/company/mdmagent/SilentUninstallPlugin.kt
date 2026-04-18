package com.company.mdmagent

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Silent Admin-Initiated Uninstall
 *
 * When admin initiates uninstall from dashboard:
 * 1. Backend generates OTP automatically
 * 2. Sends via FCM with the OTP pre-embedded (encrypted)
 * 3. App silently verifies with backend, no employee interaction needed
 * 4. Device Owner API removes uninstall block and triggers removal
 *
 * Employee-initiated uninstall always requires PIN (Section 6.1).
 */
class SilentUninstallPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private lateinit var dpm: DevicePolicyManager
    private lateinit var admin: ComponentName

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        admin = ComponentName(context, MDMDeviceAdminReceiver::class.java)
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/uninstall")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            // Admin-authorized silent uninstall — no employee interaction
            "requestUninstall" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    // 1. Remove uninstall block
                    dpm.setUninstallBlocked(admin, context.packageName, false)
                    // 2. Remove device admin (required before uninstall)
                    dpm.clearDeviceOwnerApp(context.packageName)
                    // 3. Trigger uninstall via package manager
                    val intent = android.content.Intent(
                        android.content.Intent.ACTION_UNINSTALL_PACKAGE
                    ).apply {
                        data = android.net.Uri.parse("package:${context.packageName}")
                        putExtra(android.content.Intent.EXTRA_RETURN_RESULT, true)
                        flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(intent)
                    result.success(true)
                } else {
                    // Not Device Owner — use standard uninstall request
                    val intent = android.content.Intent(
                        android.content.Intent.ACTION_DELETE
                    ).apply {
                        data = android.net.Uri.parse("package:${context.packageName}")
                        flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(intent)
                    result.success(false) // not silent — will show system dialog
                }
            }

            // Block uninstall (called on enrollment)
            "blockUninstall" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setUninstallBlocked(admin, context.packageName, true)
                    result.success(true)
                } else {
                    result.success(false)
                }
            }

            // Check if uninstall is currently blocked
            "isUninstallBlocked" -> {
                val blocked = dpm.isDeviceOwnerApp(context.packageName) &&
                    dpm.isUninstallBlocked(admin, context.packageName)
                result.success(blocked)
            }

            else -> result.notImplemented()
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
