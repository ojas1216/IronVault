package com.company.mdmagent

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.Build
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Section 6 — Uninstall & Tamper Resistance
 *
 * All restrictions use DevicePolicyManager official API — no exploits.
 * Requires Device Owner privileges provisioned via Android Enterprise.
 */
class TamperPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private lateinit var dpm: DevicePolicyManager
    private lateinit var admin: ComponentName

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        admin = ComponentName(context, MDMDeviceAdminReceiver::class.java)
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/tamper")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {

            // 6.4 — Block airplane mode (Device Owner)
            "blockAirplaneMode" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setSecureSetting(admin,
                        android.provider.Settings.Global.AIRPLANE_MODE_ON, "0")
                    // Restrict user from toggling it
                    dpm.addUserRestriction(admin,
                        android.os.UserManager.DISALLOW_AIRPLANE_MODE)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            "unblockAirplaneMode" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.clearUserRestriction(admin,
                        android.os.UserManager.DISALLOW_AIRPLANE_MODE)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            // 6.3 — Lock power menu (API 30+)
            "lockPowerMenu" -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
                    dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setGlobalSetting(admin, "power_button_suppression_delay_ms", "30000")
                    result.success(true)
                } else {
                    result.success(false)
                }
            }

            // 6.5 — Start watchdog service
            "startWatchdog" -> {
                val intent = android.content.Intent(context, WatchdogService::class.java)
                context.startForegroundService(intent)
                result.success(true)
            }

            // 6.1 — Validate PIN (stored in secure prefs, set during enrollment)
            "validatePin" -> {
                val entered = call.argument<String>("pin") ?: ""
                val storedHash = context
                    .getSharedPreferences("mdm_secure", Context.MODE_PRIVATE)
                    .getString("admin_pin_hash", null)
                val valid = storedHash != null &&
                        java.security.MessageDigest.getInstance("SHA-256")
                            .digest(entered.toByteArray())
                            .let { java.util.Base64.getEncoder().encodeToString(it) } == storedHash
                result.success(valid)
            }

            else -> result.notImplemented()
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
