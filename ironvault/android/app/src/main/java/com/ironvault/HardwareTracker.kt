package com.ironvault

import android.bluetooth.BluetoothManager
import android.content.Context
import android.net.wifi.WifiManager
import android.os.Build
import android.view.Display
import android.view.WindowManager
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.security.KeyStore
import java.security.MessageDigest

data class HardwareComponents(
    val socManufacturer: String,
    val socModel: String,
    val emmcCid: String?,        // Root only
    val wifiMac: String?,
    val btMac: String?,
    val displayUniqueId: String?,
    val boardName: String,
    val cpuAbi: String,
    val compositeFingerprint: String,
)

object HardwareTracker {

    private const val KEYSTORE_ALIAS = "ironvault_golden_fingerprint"
    private const val PREFS_FILE = "ironvault_hw_prefs"
    private const val PREF_GOLDEN_FINGERPRINT = "golden_fingerprint"
    private const val PREF_FINGERPRINT_SET = "fingerprint_set"
    private const val MISMATCH_THRESHOLD = 3 // How many component mismatches trigger brick

    suspend fun readHardwareComponents(context: Context): HardwareComponents = withContext(Dispatchers.IO) {
        val emmcCid = readEmmcCid()
        val wifiMac = readWifiMac(context)
        val btMac = readBtMac(context)
        val displayId = readDisplayUniqueId(context)

        val components = HardwareComponents(
            socManufacturer = Build.SOC_MANUFACTURER,
            socModel = Build.SOC_MODEL,
            emmcCid = emmcCid,
            wifiMac = wifiMac,
            btMac = btMac,
            displayUniqueId = displayId,
            boardName = Build.BOARD,
            cpuAbi = Build.SUPPORTED_ABIS.firstOrNull() ?: Build.CPU_ABI,
            compositeFingerprint = computeCompositeFingerprint(
                emmcCid, wifiMac, btMac, displayId
            )
        )
        components
    }

    private fun readEmmcCid(): String? {
        // Requires root — attempt to read from sysfs
        return try {
            val cidFile = File("/sys/block/mmcblk0/device/cid")
            if (cidFile.canRead()) cidFile.readText().trim()
            else {
                // Fallback: try mmcblk1 (some devices use different numbering)
                val alt = File("/sys/block/mmcblk1/device/cid")
                if (alt.canRead()) alt.readText().trim() else null
            }
        } catch (_: Exception) { null }
    }

    private fun readWifiMac(context: Context): String? {
        // Note: Android 10+ returns randomized MAC for privacy
        // Only true MAC available with system privileges or root
        return try {
            // Try reading from sysfs (requires root)
            val macFile = File("/sys/class/net/wlan0/address")
            if (macFile.canRead()) {
                val mac = macFile.readText().trim()
                if (mac != "02:00:00:00:00:00") mac else null
            } else {
                // Fallback to WifiManager (may be randomized)
                @Suppress("DEPRECATION")
                val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
                wm.connectionInfo?.macAddress?.takeIf { it != "02:00:00:00:00:00" }
            }
        } catch (_: Exception) { null }
    }

    private fun readBtMac(context: Context): String? {
        return try {
            // Try sysfs first (root)
            val btFile = File("/sys/class/bluetooth/hci0/address")
            if (btFile.canRead()) btFile.readText().trim()
            else {
                // Non-root fallback
                val bm = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
                bm.adapter?.address?.takeIf { it != "02:00:00:00:00:00" }
            }
        } catch (_: Exception) { null }
    }

    private fun readDisplayUniqueId(context: Context): String? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
                wm.defaultDisplay.uniqueId
            } else null
        } catch (_: Exception) { null }
    }

    private fun computeCompositeFingerprint(
        emmcCid: String?,
        wifiMac: String?,
        btMac: String?,
        displayId: String?,
    ): String {
        val parts = listOfNotNull(
            Build.BOARD,
            Build.BRAND,
            Build.DEVICE,
            Build.HARDWARE,
            Build.MANUFACTURER,
            Build.MODEL,
            Build.SOC_MANUFACTURER,
            Build.SOC_MODEL,
            Build.SUPPORTED_ABIS.joinToString(","),
            emmcCid,
            wifiMac,
            btMac,
            displayId,
        ).joinToString("|")

        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(parts.toByteArray()).joinToString("") { "%02x".format(it) }
    }

    // ─── Golden Fingerprint Management ───────────────────────────────────────

    fun saveGoldenFingerprint(context: Context, fingerprint: String) {
        getEncryptedPrefs(context).edit()
            .putString(PREF_GOLDEN_FINGERPRINT, fingerprint)
            .putBoolean(PREF_FINGERPRINT_SET, true)
            .apply()
    }

    fun getGoldenFingerprint(context: Context): String? {
        return getEncryptedPrefs(context).getString(PREF_GOLDEN_FINGERPRINT, null)
    }

    fun isGoldenFingerprintSet(context: Context): Boolean {
        return getEncryptedPrefs(context).getBoolean(PREF_FINGERPRINT_SET, false)
    }

    private fun getEncryptedPrefs(context: Context): android.content.SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        return EncryptedSharedPreferences.create(
            context,
            PREFS_FILE,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    // ─── Fingerprint Verification ─────────────────────────────────────────────

    suspend fun verifyFingerprintOnBoot(context: Context): FingerprintVerificationResult {
        val golden = getGoldenFingerprint(context)
            ?: return FingerprintVerificationResult.NOT_SET

        val current = readHardwareComponents(context).compositeFingerprint

        return if (current == golden) {
            FingerprintVerificationResult.MATCH
        } else {
            FingerprintVerificationResult.MISMATCH
        }
    }

    enum class FingerprintVerificationResult {
        MATCH, MISMATCH, NOT_SET
    }
}
