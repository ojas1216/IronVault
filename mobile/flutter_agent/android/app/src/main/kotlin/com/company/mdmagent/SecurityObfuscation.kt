package com.company.mdmagent

import android.content.Context
import android.os.Debug
import java.io.File
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec
import android.util.Base64

/**
 * Anti-reverse-engineering measures.
 * - Detects debugger attachment
 * - Detects emulator (for bypass attempts)
 * - Detects Frida/Xposed hooking framework injection
 * - String encryption utilities
 *
 * These protect the company's proprietary MDM logic from being
 * cracked or bypassed by unauthorized persons.
 */
object SecurityObfuscation {

    // ── Anti-debugging ────────────────────────────────────────────────────
    fun isDebuggerAttached(): Boolean {
        return Debug.isDebuggerConnected() || Debug.waitingForDebugger()
    }

    // ── Emulator detection (attackers often test bypasses on emulators) ──
    fun isEmulator(): Boolean {
        return (android.os.Build.FINGERPRINT.startsWith("generic")
                || android.os.Build.FINGERPRINT.startsWith("unknown")
                || android.os.Build.MODEL.contains("google_sdk")
                || android.os.Build.MODEL.contains("Emulator")
                || android.os.Build.MODEL.contains("Android SDK built for x86")
                || android.os.Build.MANUFACTURER.contains("Genymotion")
                || android.os.Build.BRAND.startsWith("generic")
                || android.os.Build.DEVICE.startsWith("generic"))
    }

    // ── Frida / Xposed detection ──────────────────────────────────────────
    fun isHookingFrameworkPresent(context: Context): Boolean {
        // Check for Frida server files
        val fridaPaths = listOf(
            "/data/local/tmp/frida-server",
            "/data/local/tmp/re.frida.server",
            "/system/lib/libfrida-gadget.so",
        )
        if (fridaPaths.any { File(it).exists() }) return true

        // Check for Xposed in stack trace
        try {
            throw Exception()
        } catch (e: Exception) {
            val stack = e.stackTraceToString()
            if (stack.contains("XposedBridge") || stack.contains("de.robv.android.xposed")) {
                return true
            }
        }

        // Check for suspicious loaded libraries
        try {
            val maps = File("/proc/self/maps").readText()
            if (maps.contains("frida") || maps.contains("xposed")) return true
        } catch (_: Exception) {}

        return false
    }

    // ── APK signature verification ────────────────────────────────────────
    // Ensures the APK hasn't been repackaged/tampered with
    fun verifyApkSignature(context: Context): Boolean {
        return try {
            val pm = context.packageManager
            val signatures = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                pm.getPackageInfo(context.packageName,
                    android.content.pm.PackageManager.GET_SIGNING_CERTIFICATES)
                    .signingInfo.apkContentsSigners
            } else {
                @Suppress("DEPRECATION")
                pm.getPackageInfo(context.packageName,
                    android.content.pm.PackageManager.GET_SIGNATURES).signatures
            }
            val certHash = MessageDigest.getInstance("SHA-256")
                .digest(signatures[0].toByteArray())
                .joinToString("") { "%02x".format(it) }

            // Compare against hardcoded expected hash of your release certificate
            // Generate this during build: keytool -list -v -keystore release.keystore
            certHash == BuildConfig.EXPECTED_CERT_HASH
        } catch (_: Exception) {
            false
        }
    }

    // ── String encryption / decryption (AES-256-CBC + PBKDF2) ────────────
    // Use this to store sensitive strings in code without plaintext exposure
    fun encrypt(plaintext: String, password: String): String {
        val salt = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }
        val iv = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }
        val key = deriveKey(password, salt)
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.ENCRYPT_MODE, key, IvParameterSpec(iv))
        val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        val result = salt + iv + ciphertext
        return Base64.encodeToString(result, Base64.NO_WRAP)
    }

    fun decrypt(encoded: String, password: String): String {
        val data = Base64.decode(encoded, Base64.NO_WRAP)
        val salt = data.copyOfRange(0, 16)
        val iv = data.copyOfRange(16, 32)
        val ciphertext = data.copyOfRange(32, data.size)
        val key = deriveKey(password, salt)
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.DECRYPT_MODE, key, IvParameterSpec(iv))
        return String(cipher.doFinal(ciphertext), Charsets.UTF_8)
    }

    private fun deriveKey(password: String, salt: ByteArray): SecretKeySpec {
        val spec = PBEKeySpec(password.toCharArray(), salt, 65536, 256)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        return SecretKeySpec(factory.generateSecret(spec).encoded, "AES")
    }

    // ── Run all security checks and terminate if tampering detected ───────
    fun enforceSecurityChecks(context: Context, onViolation: (String) -> Unit) {
        if (isDebuggerAttached()) {
            onViolation("DEBUGGER_ATTACHED")
            return
        }
        if (isHookingFrameworkPresent(context)) {
            onViolation("HOOKING_FRAMEWORK")
            return
        }
        // Note: Emulator check is skipped for internal testing builds
        // Enable in production via BuildConfig.ENFORCE_EMULATOR_CHECK
        if (BuildConfig.ENFORCE_EMULATOR_CHECK && isEmulator()) {
            onViolation("EMULATOR_DETECTED")
            return
        }
        if (!verifyApkSignature(context)) {
            onViolation("SIGNATURE_MISMATCH")
        }
    }
}
