package com.company.mdmagent

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Section 4 — IMEI & Device Identity Layer
 *
 * IMEI access on Android 10+ (API 29+):
 *   - Requires READ_PRIVILEGED_PHONE_STATE (system/privileged app)
 *   - Available to Device Owner apps via DevicePolicyManager
 *   - On non-Device-Owner builds returns null gracefully
 */
class DeviceIdentityPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/identity")
        channel.setMethodCallHandler(this)
    }

    @SuppressLint("HardwareIds", "MissingPermission")
    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "getImei" -> {
                val slot = call.argument<Int>("slot") ?: 0
                result.success(getImei(slot))
            }
            "getSerial" -> result.success(getSerial())
            "getAndroidId" -> result.success(getAndroidId())
            else -> result.notImplemented()
        }
    }

    @SuppressLint("MissingPermission")
    private fun getImei(slot: Int): String? {
        return try {
            val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                tm.getImei(slot) // requires READ_PRIVILEGED_PHONE_STATE or Device Owner
            } else {
                @Suppress("DEPRECATION")
                tm.deviceId
            }
        } catch (e: SecurityException) {
            null // Not device owner — return null, don't crash
        } catch (_: Exception) {
            null
        }
    }

    @SuppressLint("HardwareIds")
    private fun getSerial(): String? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Build.getSerial() // requires READ_PRIVILEGED_PHONE_STATE or Device Owner
            } else {
                @Suppress("DEPRECATION")
                Build.SERIAL
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun getAndroidId(): String {
        return Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ANDROID_ID,
        )
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
