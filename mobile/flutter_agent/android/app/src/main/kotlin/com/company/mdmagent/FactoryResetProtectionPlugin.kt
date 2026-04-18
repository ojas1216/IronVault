package com.company.mdmagent

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.os.UserManager
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Factory Reset Protection (FRP) — Legitimate OS-level approach.
 *
 * HOW IT WORKS (Android Device Owner):
 * 1. When device is factory reset, Android FRP requires the Google account
 *    that was logged in before reset — users CANNOT bypass this.
 * 2. With Device Owner + setFactoryResetProtectionPolicy(), we add company
 *    Google account as the allowed account — employees cannot bypass FRP.
 * 3. After authorized factory reset, Zero-touch enrollment (DEP) ensures
 *    the MDM app is automatically reinstalled on first boot.
 *
 * This is the ONLY OS-compliant way to survive factory reset.
 * We do NOT inject into system partition or exploit kernel vulnerabilities.
 */
class FactoryResetProtectionPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private lateinit var dpm: DevicePolicyManager
    private lateinit var admin: ComponentName

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        admin = ComponentName(context, MDMDeviceAdminReceiver::class.java)
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/frp")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {

            // Lock factory reset — requires admin account to setup after reset
            "enableFactoryResetProtection" -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
                    dpm.isDeviceOwnerApp(context.packageName)) {
                    try {
                        // Require company Google account after any factory reset
                        val companyAccount = call.argument<String>("company_account")
                            ?: "it-admin@yourcompany.com"
                        val policy = android.app.admin.FactoryResetProtectionPolicy.Builder()
                            .setFactoryResetProtectionAccounts(listOf(companyAccount))
                            .setFactoryResetProtectionEnabled(true)
                            .build()
                        dpm.setFactoryResetProtectionPolicy(admin, policy)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("FRP_ERROR", e.message, null)
                    }
                } else {
                    result.success(false) // Not device owner or SDK too low
                }
            }

            // Block unauthorized factory reset attempts
            "blockFactoryReset" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    // Prevent user from performing factory reset via Settings
                    dpm.addUserRestriction(admin, UserManager.DISALLOW_FACTORY_RESET)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            // Allow factory reset (called when admin authorized)
            "allowFactoryReset" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.clearUserRestriction(admin, UserManager.DISALLOW_FACTORY_RESET)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            // Block safe mode (prevents bypassing our policies via safe mode boot)
            "blockSafeMode" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.addUserRestriction(admin, UserManager.DISALLOW_SAFE_BOOT)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            // Block USB debugging (prevents ADB bypass attempts)
            "blockUsbDebugging" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setSecureSetting(admin,
                        android.provider.Settings.Global.ADB_ENABLED, "0")
                    dpm.addUserRestriction(admin,
                        UserManager.DISALLOW_DEBUGGING_FEATURES)
                    result.success(true)
                } else {
                    result.error("NOT_OWNER", "Requires Device Owner", null)
                }
            }

            "isFrpEnabled" -> {
                val isEnabled = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
                    dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.getFactoryResetProtectionPolicy(admin)?.isFactoryResetProtectionEnabled ?: false
                } else false
                result.success(isEnabled)
            }

            else -> result.notImplemented()
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
