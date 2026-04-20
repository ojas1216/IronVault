package com.company.mdmagent

import android.annotation.SuppressLint
import android.bluetooth.BluetoothManager
import android.content.Context
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.MessageDigest

/**
 * Section 4 — IMEI & Device Identity Layer
 *
 * Exposes hardware identifiers for composite fingerprinting:
 *   - IMEI (slot 0 and 1) — requires Device Owner on Android 10+
 *   - Device serial number — requires Device Owner on Android 10+
 *   - Android ID (stable per device + app signing key)
 *   - WiFi MAC address (from sysfs — no runtime permission needed)
 *   - Bluetooth MAC address
 *   - SoC manufacturer and model (Android 12+)
 *   - Firmware fingerprint (SHA-256 of build + bootloader + security patch)
 *   - Extended hardware fingerprint (SHA-256 of all components)
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
            "getImei"                  -> result.success(getImei(call.argument<Int>("slot") ?: 0))
            "getSerial"                -> result.success(getSerial())
            "getAndroidId"             -> result.success(getAndroidId())
            "getWifiMac"               -> result.success(getWifiMac())
            "getBluetoothMac"          -> result.success(getBluetoothMac())
            "getSocInfo"               -> result.success(getSocInfo())
            "getFirmwareFingerprint"   -> result.success(getFirmwareFingerprint())
            "getExtendedFingerprint"   -> result.success(getExtendedFingerprint())
            else                       -> result.notImplemented()
        }
    }

    @SuppressLint("MissingPermission")
    private fun getImei(slot: Int): String? {
        return try {
            val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                tm.getImei(slot)
            } else {
                @Suppress("DEPRECATION")
                tm.deviceId
            }
        } catch (_: Exception) { null }
    }

    @SuppressLint("HardwareIds")
    private fun getSerial(): String? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Build.getSerial()
            else @Suppress("DEPRECATION") Build.SERIAL
        } catch (_: Exception) { null }
    }

    private fun getAndroidId(): String =
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)

    private fun getWifiMac(): String? {
        return try {
            // sysfs gives the real persistent MAC regardless of Android MAC randomisation setting
            val candidates = listOf(
                "/sys/class/net/wlan0/address",
                "/sys/class/net/wlan1/address",
            )
            candidates.firstNotNullOfOrNull { path ->
                val f = File(path)
                if (f.exists() && f.canRead()) f.readText().trim().takeIf { it.isNotBlank() && it != "00:00:00:00:00:00" }
                else null
            }
        } catch (_: Exception) { null }
    }

    @SuppressLint("MissingPermission")
    private fun getBluetoothMac(): String? {
        return try {
            val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
            bm?.adapter?.address?.takeIf { it.isNotBlank() && it != "02:00:00:00:00:00" }
        } catch (_: Exception) { null }
    }

    private fun getSocInfo(): Map<String, String?> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            mapOf("soc_manufacturer" to Build.SOC_MANUFACTURER, "soc_model" to Build.SOC_MODEL)
        } else {
            mapOf("soc_manufacturer" to null, "soc_model" to null)
        }
    }

    /**
     * Firmware fingerprint — detects bootloader and OS updates/tampering.
     * SHA-256 of: build fingerprint | bootloader | security patch | OS codename
     */
    fun getFirmwareFingerprint(): String {
        val parts = listOf(
            Build.FINGERPRINT,
            Build.BOOTLOADER,
            Build.VERSION.SECURITY_PATCH,
            Build.VERSION.CODENAME,
        ).joinToString("|")
        return sha256(parts)
    }

    /**
     * Extended hardware fingerprint — most tamper-resistant identifier.
     * Combines board, SoC, WiFi MAC, Bluetooth MAC, serial.
     * Any hardware swap will change this fingerprint.
     */
    fun getExtendedFingerprint(): String {
        val serial = try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Build.getSerial() else ""
        } catch (_: Exception) { "" }

        val socManufacturer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MANUFACTURER else ""
        val socModel = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MODEL else ""

        val parts = listOf(
            Build.BOARD,
            Build.BRAND,
            Build.DEVICE,
            Build.HARDWARE,
            Build.MANUFACTURER,
            Build.MODEL,
            Build.PRODUCT,
            socManufacturer,
            socModel,
            getWifiMac() ?: "",
            getBluetoothMac() ?: "",
            serial,
        ).joinToString("|")
        return sha256(parts)
    }

    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }
}
