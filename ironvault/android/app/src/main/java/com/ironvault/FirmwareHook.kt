package com.ironvault

import android.content.Context
import android.os.Build
import android.system.Os
import java.io.File
import java.security.MessageDigest
import android.util.Log

object FirmwareHook {

    private const val TAG = "FirmwareHook"

    data class FirmwareState(
        val bootloaderStatus: String,
        val verifiedBootState: String,
        val secureBootEnabled: Boolean,
        val oemUnlockEnabled: Boolean,
        val bootloaderVersion: String,
        val firmwareFingerprint: String,
        val systemPartitionHash: String,
        val isCompromised: Boolean,
        val compromiseReason: String?
    )

    fun verifyFirmwareIntegrity(context: Context): FirmwareState {
        val bootloaderStatus = getBootloaderStatus()
        val verifiedBootState = getVerifiedBootState()
        val secureBootEnabled = isSecureBootEnabled()
        val oemUnlockEnabled = isOemUnlockEnabled()
        val bootloaderVersion = Build.BOOTLOADER
        val firmwareFingerprint = buildFirmwareFingerprint()
        val systemPartitionHash = hashSystemPartition()

        val (isCompromised, reason) = detectCompromise(
            bootloaderStatus, verifiedBootState, secureBootEnabled, oemUnlockEnabled
        )

        return FirmwareState(
            bootloaderStatus = bootloaderStatus,
            verifiedBootState = verifiedBootState,
            secureBootEnabled = secureBootEnabled,
            oemUnlockEnabled = oemUnlockEnabled,
            bootloaderVersion = bootloaderVersion,
            firmwareFingerprint = firmwareFingerprint,
            systemPartitionHash = systemPartitionHash,
            isCompromised = isCompromised,
            compromiseReason = reason
        )
    }

    private fun getBootloaderStatus(): String {
        return try {
            Build.BOOTLOADER.also {
                Log.d(TAG, "Bootloader: $it")
            }
        } catch (e: Exception) {
            "UNKNOWN"
        }
    }

    private fun getVerifiedBootState(): String {
        return try {
            val prop = readSystemProp("ro.boot.verifiedbootstate")
            prop.ifEmpty { readSystemProp("ro.boot.flash.locked").let { if (it == "1") "green" else "orange" } }
        } catch (e: Exception) {
            "UNKNOWN"
        }
    }

    private fun isSecureBootEnabled(): Boolean {
        return try {
            val verifiedBootState = getVerifiedBootState()
            val flashLocked = readSystemProp("ro.boot.flash.locked")
            verifiedBootState == "green" || flashLocked == "1"
        } catch (e: Exception) {
            false
        }
    }

    private fun isOemUnlockEnabled(): Boolean {
        return try {
            val verifiedBootState = getVerifiedBootState()
            verifiedBootState == "orange" || verifiedBootState == "red"
        } catch (e: Exception) {
            false
        }
    }

    private fun buildFirmwareFingerprint(): String {
        val components = listOf(
            Build.FINGERPRINT,
            Build.BOOTLOADER,
            readSystemProp("ro.build.version.security_patch"),
            readSystemProp("ro.build.tags"),
            readSystemProp("ro.boot.vbmeta.digest")
        )
        val combined = components.joinToString("|")
        return sha256(combined)
    }

    private fun hashSystemPartition(): String {
        return try {
            val buildPropFile = File("/system/build.prop")
            if (buildPropFile.exists() && buildPropFile.canRead()) {
                sha256(buildPropFile.readText())
            } else {
                sha256(Build.FINGERPRINT + Build.TIME.toString())
            }
        } catch (e: Exception) {
            sha256(Build.FINGERPRINT)
        }
    }

    private fun detectCompromise(
        bootloaderStatus: String,
        verifiedBootState: String,
        secureBootEnabled: Boolean,
        oemUnlockEnabled: Boolean
    ): Pair<Boolean, String?> {
        if (verifiedBootState == "red") {
            return Pair(true, "Verified boot failed: dm-verity violation detected")
        }
        if (oemUnlockEnabled && verifiedBootState == "orange") {
            return Pair(true, "OEM unlock enabled: bootloader is unlocked")
        }
        if (!secureBootEnabled) {
            return Pair(true, "Secure boot is not enabled on this device")
        }
        if (isRooted()) {
            return Pair(true, "Root access detected: system integrity compromised")
        }
        return Pair(false, null)
    }

    private fun isRooted(): Boolean {
        val rootPaths = listOf(
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/system/bin/failsafe/su",
            "/data/local/su",
            "/su/bin/su"
        )
        return rootPaths.any { File(it).exists() }
    }

    private fun readSystemProp(propName: String): String {
        return try {
            val process = Runtime.getRuntime().exec(arrayOf("getprop", propName))
            process.inputStream.bufferedReader().readLine()?.trim() ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    private fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(input.toByteArray(Charsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }
    }

    fun getBootTimeFingerprint(): Map<String, String> {
        return mapOf(
            "bootloader" to Build.BOOTLOADER,
            "verified_boot_state" to getVerifiedBootState(),
            "security_patch" to Build.VERSION.SECURITY_PATCH,
            "build_fingerprint" to Build.FINGERPRINT,
            "vbmeta_digest" to readSystemProp("ro.boot.vbmeta.digest"),
            "flash_locked" to readSystemProp("ro.boot.flash.locked"),
            "firmware_fingerprint" to buildFirmwareFingerprint()
        )
    }
}
