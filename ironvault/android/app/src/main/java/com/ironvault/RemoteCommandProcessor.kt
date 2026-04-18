package com.ironvault

import android.app.admin.DevicePolicyManager
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.os.Build
import android.telephony.SmsMessage
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.*
import org.json.JSONObject
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec
import android.util.Base64

// ─── FCM Service ─────────────────────────────────────────────────────────────

class IronVaultFCMService : FirebaseMessagingService() {

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val commandType = data["command"] ?: return
        val payload = data["payload"]?.let { runCatching { JSONObject(it) }.getOrNull() }

        CoroutineScope(Dispatchers.IO).launch {
            RemoteCommandProcessor.execute(applicationContext, RemoteCommand(
                type = commandType,
                payload = payload ?: JSONObject(),
                commandId = data["command_id"] ?: "",
                preVerified = data["pre_verified"] == "true",
            ))
        }
    }

    override fun onNewToken(token: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val prefs = getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
                prefs.edit().putString("fcm_token", token).apply()
                val deviceId = prefs.getString("device_id", "") ?: return@launch
                DeviceRepository(applicationContext).updatePushToken(deviceId, token)
            } catch (_: Exception) {}
        }
    }
}

// ─── Command Model ────────────────────────────────────────────────────────────

data class RemoteCommand(
    val type: String,
    val payload: JSONObject,
    val commandId: String,
    val preVerified: Boolean = false,
)

// ─── Command Processor ────────────────────────────────────────────────────────

object RemoteCommandProcessor {

    private var alarmPlayer: MediaPlayer? = null

    suspend fun execute(context: Context, command: RemoteCommand) {
        when (command.type.uppercase()) {
            "LOCK"       -> executeLock(context)
            "ALARM"      -> executeAlarm(context)
            "STOP_ALARM" -> stopAlarm()
            "LOCATION"   -> executeLocation(context, command.commandId)
            "WIPE"       -> executeWipe(context, command)
            "PHOTO"      -> executePhoto(context, command.commandId)
            "SIMDUMP"    -> executeSimDump(context, command.commandId)
            "DEVICEINFO" -> executeDeviceInfo(context, command.commandId)
            "LOST_MODE"  -> executeLostMode(context)
            "UNLOCK"     -> executeUnlock(context)
            "BRICK"      -> executeBrick(context)
            "UNBRICK"    -> executeUnbrick(context, command)
        }
        // Acknowledge command
        acknowledgeCommand(context, command.commandId, "executed")
    }

    private fun executeLock(context: Context) {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        try {
            dpm.lockNow()
        } catch (_: SecurityException) {
            // Fallback: show stolen overlay
            val intent = Intent(context, BrickActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                putExtra("mode", "lock")
            }
            context.startActivity(intent)
        }
    }

    private fun executeAlarm(context: Context) {
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audio.setStreamVolume(
            AudioManager.STREAM_ALARM,
            audio.getStreamMaxVolume(AudioManager.STREAM_ALARM),
            0
        )
        val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
        alarmPlayer?.release()
        alarmPlayer = MediaPlayer.create(context, uri)?.apply {
            isLooping = true
            start()
        }
    }

    private fun stopAlarm() {
        alarmPlayer?.apply { stop(); release() }
        alarmPlayer = null
    }

    private suspend fun executeLocation(context: Context, commandId: String) {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
        try {
            val loc = lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
            val result = mapOf(
                "latitude" to (loc?.latitude ?: 0.0),
                "longitude" to (loc?.longitude ?: 0.0),
                "accuracy" to (loc?.accuracy ?: 0f),
                "timestamp" to (loc?.time ?: 0L),
                "provider" to (loc?.provider ?: "unknown"),
            )
            DeviceRepository(context).sendCommandResult(commandId, result)
        } catch (e: SecurityException) {
            DeviceRepository(context).sendCommandResult(commandId, mapOf("error" to "location_permission_denied"))
        }
    }

    private fun executeWipe(context: Context, command: RemoteCommand) {
        if (!command.preVerified) return // Safety gate
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        try {
            dpm.wipeData(DevicePolicyManager.WIPE_EXTERNAL_STORAGE or DevicePolicyManager.WIPE_RESET_PROTECTION_DATA)
        } catch (_: SecurityException) {}
    }

    private suspend fun executePhoto(context: Context, commandId: String) {
        try {
            val photoPath = CameraHelper.captureSecurityPhoto(context)
            if (photoPath != null) {
                DeviceRepository(context).uploadPhoto(commandId, photoPath)
            }
        } catch (_: Exception) {}
    }

    private suspend fun executeSimDump(context: Context, commandId: String) {
        val sims = SIMIntelligence.extractAllSims(context)
        val result = mapOf("sims" to sims.map { sim ->
            mapOf(
                "slot" to sim.slot,
                "iccid" to (sim.iccid ?: ""),
                "carrier" to (sim.carrier ?: ""),
                "mcc" to (sim.mcc ?: ""),
                "mnc" to (sim.mnc ?: ""),
                "country" to (sim.countryIso ?: ""),
                "roaming" to sim.isRoaming,
            )
        })
        DeviceRepository(context).sendCommandResult(commandId, result)
    }

    private suspend fun executeDeviceInfo(context: Context, commandId: String) {
        val identity = IMSIProcessor.extractIdentity(context)
        val result = mapOf(
            "imei" to (identity.imei ?: ""),
            "imei2" to (identity.imei2 ?: ""),
            "serial" to (identity.serial ?: ""),
            "android_id" to identity.androidId,
            "hardware_fingerprint" to identity.hardwareFingerprint,
            "manufacturer" to identity.manufacturer,
            "model" to identity.model,
            "sdk_version" to identity.sdkVersion,
        )
        DeviceRepository(context).sendCommandResult(commandId, result)
    }

    private fun executeLostMode(context: Context) {
        val intent = Intent(context, BrickActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("mode", "lost")
        }
        context.startActivity(intent)
    }

    private fun executeUnlock(context: Context) {
        // Dismiss brick/lost mode
        context.sendBroadcast(Intent(BrickMode.ACTION_DISMISS_BRICK))
    }

    private fun executeBrick(context: Context) {
        BrickMode.activate(context, "remote_command")
    }

    private fun executeUnbrick(context: Context, command: RemoteCommand) {
        val token = command.payload.optString("unlock_token")
        if (UnlockTokenValidator.validate(context, token)) {
            BrickMode.deactivate(context)
        }
    }

    private suspend fun acknowledgeCommand(context: Context, commandId: String, status: String) {
        if (commandId.isBlank()) return
        try {
            DeviceRepository(context).acknowledgeCommand(commandId, status)
        } catch (_: Exception) {}
    }
}

// ─── SMS Command Parser ───────────────────────────────────────────────────────

object SMSCommandParser {

    private const val SMS_PREFIX = "IVX:"

    fun parseSMS(context: Context, intent: Intent) {
        val messages = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            intent.getSerializableExtra("pdus") as? Array<*>
        } else null ?: return

        for (pdu in messages) {
            val sms = SmsMessage.createFromPdu(pdu as ByteArray)
            val body = sms.messageBody ?: continue
            if (!body.startsWith(SMS_PREFIX)) continue

            val encrypted = body.removePrefix(SMS_PREFIX).trim()
            val decrypted = decryptSMSCommand(context, encrypted) ?: continue

            try {
                val json = JSONObject(decrypted)
                val commandType = json.getString("cmd")
                val commandId = json.optString("id", "sms_${System.currentTimeMillis()}")
                val payload = json.optJSONObject("data") ?: JSONObject()

                CoroutineScope(Dispatchers.IO).launch {
                    RemoteCommandProcessor.execute(context, RemoteCommand(
                        type = commandType,
                        payload = payload,
                        commandId = commandId,
                        preVerified = json.optBoolean("verified", false),
                    ))
                }
            } catch (_: Exception) {}
        }
    }

    private fun decryptSMSCommand(context: Context, encrypted: String): String? {
        return try {
            val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val keyHex = prefs.getString("sms_aes_key", null) ?: return null
            val keyBytes = hexToBytes(keyHex)
            val data = Base64.decode(encrypted, Base64.DEFAULT)

            // First 16 bytes are IV
            val iv = data.sliceArray(0 until 16)
            val ciphertext = data.sliceArray(16 until data.size)

            val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
            cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(keyBytes, "AES"), IvParameterSpec(iv))
            String(cipher.doFinal(ciphertext), Charsets.UTF_8)
        } catch (_: Exception) { null }
    }

    private fun hexToBytes(hex: String): ByteArray {
        return ByteArray(hex.length / 2) { i -> hex.substring(i * 2, i * 2 + 2).toInt(16).toByte() }
    }
}

// ─── Unlock Token Validator ───────────────────────────────────────────────────

object UnlockTokenValidator {
    fun validate(context: Context, token: String): Boolean {
        if (token.isBlank()) return false
        return try {
            val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val deviceId = prefs.getString("device_id", "") ?: return false
            val secret = prefs.getString("device_secret", "") ?: return false
            // Token = HMAC-SHA256(deviceId + "|" + timestamp_floor_to_hour, secret)
            // Valid if token matches current or previous hour
            val now = System.currentTimeMillis() / 3_600_000
            listOf(now, now - 1).any { hour ->
                val expected = hmacSha256("${deviceId}|${hour}", secret)
                constantTimeEquals(expected, token)
            }
        } catch (_: Exception) { false }
    }

    private fun hmacSha256(data: String, key: String): String {
        val mac = javax.crypto.Mac.getInstance("HmacSHA256")
        mac.init(javax.crypto.spec.SecretKeySpec(key.toByteArray(), "HmacSHA256"))
        return mac.doFinal(data.toByteArray()).joinToString("") { "%02x".format(it) }
    }

    private fun constantTimeEquals(a: String, b: String): Boolean {
        if (a.length != b.length) return false
        var result = 0
        for (i in a.indices) result = result or (a[i].code xor b[i].code)
        return result == 0
    }
}
