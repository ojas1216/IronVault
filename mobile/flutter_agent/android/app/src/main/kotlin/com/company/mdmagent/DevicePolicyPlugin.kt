package com.company.mdmagent

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

class DevicePolicyPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var channel: MethodChannel
    private lateinit var context: Context
    private lateinit var dpm: DevicePolicyManager
    private lateinit var adminComponent: ComponentName

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        adminComponent = ComponentName(context, MDMDeviceAdminReceiver::class.java)

        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/dpm")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "lockDevice" -> {
                dpm.lockNow()
                result.success(null)
            }
            "wipeDevice" -> {
                // Factory reset — irreversible
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.wipeData(DevicePolicyManager.WIPE_EXTERNAL_STORAGE)
                    result.success(null)
                } else {
                    result.error("NOT_OWNER", "Not device owner", null)
                }
            }
            "enableLostMode" -> {
                val message = call.argument<String>("message") ?: "This device is lost. Contact IT."
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    // Set lock task message visible on lock screen
                    dpm.setDeviceOwnerLockScreenInfo(adminComponent, message)
                    dpm.lockNow()
                    result.success(null)
                } else {
                    result.error("NOT_OWNER", "Not device owner", null)
                }
            }
            "blockUninstall" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setUninstallBlocked(
                        adminComponent,
                        context.packageName,
                        true
                    )
                    result.success(null)
                } else {
                    result.error("NOT_OWNER", "Not device owner", null)
                }
            }
            "unblockUninstall" -> {
                if (dpm.isDeviceOwnerApp(context.packageName)) {
                    dpm.setUninstallBlocked(
                        adminComponent,
                        context.packageName,
                        false
                    )
                    result.success(null)
                } else {
                    result.error("NOT_OWNER", "Not device owner", null)
                }
            }
            "isDeviceOwner" -> {
                result.success(dpm.isDeviceOwnerApp(context.packageName))
            }
            else -> result.notImplemented()
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
