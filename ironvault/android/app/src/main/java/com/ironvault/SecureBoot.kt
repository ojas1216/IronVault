package com.ironvault

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.Signature
import java.util.Base64

object SecureBoot {

    private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
    private const val KEY_ALIAS = "ironvault_boot_key"
    private const val PREF_STORED_SIGNATURE = "boot_signature"

    // Called on every boot — verifies hardware fingerprint hasn't changed
    suspend fun verifyOnBoot(context: Context): BootVerificationResult = withContext(Dispatchers.IO) {
        try {
            // Step 1: Read current hardware components
            val components = HardwareTracker.readHardwareComponents(context)
            val currentFingerprint = components.compositeFingerprint

            // Step 2: Check if golden fingerprint is set
            if (!HardwareTracker.isGoldenFingerprintSet(context)) {
                // First boot — establish golden fingerprint
                HardwareTracker.saveGoldenFingerprint(context, currentFingerprint)
                storeSignedFingerprint(context, currentFingerprint)
                return@withContext BootVerificationResult.FIRST_BOOT
            }

            // Step 3: Verify golden fingerprint signature (detect tampering with stored prefs)
            val storedSig = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
                .getString(PREF_STORED_SIGNATURE, null)

            if (storedSig != null && !verifySignature(currentFingerprint, storedSig)) {
                // Fingerprint storage was tampered with
                BrickMode.activate(context, "keystore_signature_mismatch")
                return@withContext BootVerificationResult.TAMPER_DETECTED
            }

            // Step 4: Compare current vs golden
            val result = HardwareTracker.verifyFingerprintOnBoot(context)
            when (result) {
                HardwareTracker.FingerprintVerificationResult.MATCH -> {
                    logBootSuccess(context, currentFingerprint)
                    BootVerificationResult.VERIFIED
                }
                HardwareTracker.FingerprintVerificationResult.MISMATCH -> {
                    logBootFailure(context, currentFingerprint)
                    BrickMode.activate(context, "hardware_fingerprint_mismatch")
                    BootVerificationResult.TAMPER_DETECTED
                }
                HardwareTracker.FingerprintVerificationResult.NOT_SET -> {
                    BootVerificationResult.FIRST_BOOT
                }
            }
        } catch (e: Exception) {
            // Don't brick on verification error — could be legitimate API issue
            logBootError(context, e.message ?: "unknown")
            BootVerificationResult.VERIFICATION_ERROR
        }
    }

    // Store ECDSA signature of fingerprint in Android Keystore
    private fun storeSignedFingerprint(context: Context, fingerprint: String) {
        try {
            ensureKeyExists()
            val signature = signData(fingerprint)
            context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
                .edit()
                .putString(PREF_STORED_SIGNATURE, signature)
                .apply()
        } catch (_: Exception) {}
    }

    private fun ensureKeyExists() {
        val ks = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }
        if (ks.containsAlias(KEY_ALIAS)) return

        val kpg = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, KEYSTORE_PROVIDER)
        kpg.initialize(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            )
                .setAlgorithmParameterSpec(java.security.spec.ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setUserAuthenticationRequired(false) // Boot time — no biometric available
                .build()
        )
        kpg.generateKeyPair()
    }

    private fun signData(data: String): String {
        val ks = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }
        val privateKey = ks.getKey(KEY_ALIAS, null) as java.security.PrivateKey
        val sig = Signature.getInstance("SHA256withECDSA").apply {
            initSign(privateKey)
            update(data.toByteArray())
        }
        return Base64.getEncoder().encodeToString(sig.sign())
    }

    private fun verifySignature(data: String, signatureB64: String): Boolean {
        return try {
            val ks = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }
            val cert = ks.getCertificate(KEY_ALIAS) ?: return false
            val sigBytes = Base64.getDecoder().decode(signatureB64)
            val sig = Signature.getInstance("SHA256withECDSA").apply {
                initVerify(cert.publicKey)
                update(data.toByteArray())
            }
            sig.verify(sigBytes)
        } catch (_: Exception) { false }
    }

    private fun logBootSuccess(context: Context, fingerprint: String) {
        CoroutineScope(context).launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = "boot_verified:fp=${fingerprint.take(16)}...",
                    timestamp = System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    private fun logBootFailure(context: Context, currentFp: String) {
        CoroutineScope(context).launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = "boot_tamper_detected:fp=${currentFp.take(16)}...",
                    timestamp = System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    private fun logBootError(context: Context, error: String) {
        CoroutineScope(context).launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = "boot_verify_error:$error",
                    timestamp = System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    // Helper extension
    private fun CoroutineScope(context: Context) = kotlinx.coroutines.CoroutineScope(Dispatchers.IO)
}

enum class BootVerificationResult {
    VERIFIED, TAMPER_DETECTED, FIRST_BOOT, VERIFICATION_ERROR
}
