package com.ironvault

import android.content.Context
import android.net.wifi.WifiManager
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import java.security.MessageDigest

data class DeviceIdentity(
    val imei: String?,
    val imei2: String?,
    val meid: String?,
    val serial: String?,
    val androidId: String,
    val wifiMac: String?,
    val hardwareFingerprint: String,
    val socManufacturer: String,
    val socModel: String,
    val model: String,
    val manufacturer: String,
    val brand: String,
    val board: String,
    val sdkVersion: Int,
)

object IMSIProcessor {

    fun extractIdentity(context: Context): DeviceIdentity {
        val imei = getImei(context, 0)
        val imei2 = getImei(context, 1)
        val meid = getMeid(context)
        val serial = getSerial()
        val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        val wifiMac = getWifiMac(context)
        val fingerprint = buildFingerprint(imei, imei2, meid, serial, androidId, wifiMac)

        return DeviceIdentity(
            imei = imei,
            imei2 = imei2,
            meid = meid,
            serial = serial,
            androidId = androidId,
            wifiMac = wifiMac,
            hardwareFingerprint = fingerprint,
            socManufacturer = Build.SOC_MANUFACTURER,
            socModel = Build.SOC_MODEL,
            model = Build.MODEL,
            manufacturer = Build.MANUFACTURER,
            brand = Build.BRAND,
            board = Build.BOARD,
            sdkVersion = Build.VERSION.SDK_INT,
        )
    }

    private fun getImei(context: Context, slotIndex: Int): String? {
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                tm.getImei(slotIndex)
            } else {
                @Suppress("DEPRECATION")
                tm.deviceId
            }
        } catch (e: SecurityException) {
            // Requires READ_PRIVILEGED_PHONE_STATE — granted automatically to Device Owner
            null
        }
    }

    private fun getMeid(context: Context): String? {
        // CDMA fallback
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                tm.getMeid(0)
            } else null
        } catch (e: SecurityException) { null }
    }

    private fun getSerial(): String? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Build.getSerial()
            } else {
                @Suppress("DEPRECATION")
                Build.SERIAL.takeIf { it != Build.UNKNOWN }
            }
        } catch (e: SecurityException) { null }
    }

    private fun getWifiMac(context: Context): String? {
        return try {
            val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val info = wm.connectionInfo
            // Note: randomized MAC is returned for privacy on Android 10+
            // For a real MAC, require system/privileged app
            info?.macAddress?.takeIf { it != "02:00:00:00:00:00" }
        } catch (_: Exception) { null }
    }

    fun buildFingerprint(
        imei: String?,
        imei2: String?,
        meid: String?,
        serial: String?,
        androidId: String?,
        wifiMac: String?
    ): String {
        val components = listOfNotNull(
            imei?.takeIf { it.isNotBlank() },
            imei2?.takeIf { it.isNotBlank() },
            meid?.takeIf { it.isNotBlank() },
            serial?.takeIf { it.isNotBlank() },
            androidId?.takeIf { it.isNotBlank() },
            wifiMac?.takeIf { it.isNotBlank() },
            Build.BOARD,
            Build.BRAND,
            Build.DEVICE,
            Build.HARDWARE,
            Build.MANUFACTURER,
            Build.MODEL,
        ).joinToString("|")

        return sha256(components)
    }

    fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(input.toByteArray(Charsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }
    }
}
