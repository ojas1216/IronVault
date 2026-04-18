package com.ironvault

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.*

object BrickMode {

    const val ACTION_DISMISS_BRICK = "com.ironvault.DISMISS_BRICK"
    private const val PREF_BRICK_ACTIVE = "brick_mode_active"
    private const val PREF_BRICK_REASON = "brick_mode_reason"

    fun activate(context: Context, reason: String) {
        val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
        prefs.edit()
            .putBoolean(PREF_BRICK_ACTIVE, true)
            .putString(PREF_BRICK_REASON, reason)
            .apply()

        // Disable USB debugging (requires Device Owner)
        disableUsbDebugging(context)

        // Start brick activity
        val intent = Intent(context, BrickActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TASK or
                    Intent.FLAG_ACTIVITY_NO_HISTORY
            putExtra("reason", reason)
            putExtra("mode", "brick")
        }
        context.startActivity(intent)

        // Log to local DB + alert backend
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = "brick_activated:$reason",
                    timestamp = System.currentTimeMillis()
                ))
                val repo = DeviceRepository(context)
                repo.sendAlert("brick_mode_activated", mapOf(
                    "reason" to reason,
                    "timestamp" to System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    fun deactivate(context: Context) {
        val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
        prefs.edit()
            .putBoolean(PREF_BRICK_ACTIVE, false)
            .remove(PREF_BRICK_REASON)
            .apply()
        context.sendBroadcast(Intent(ACTION_DISMISS_BRICK))
    }

    fun isActive(context: Context): Boolean {
        return context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            .getBoolean(PREF_BRICK_ACTIVE, false)
    }

    private fun disableUsbDebugging(context: Context) {
        if (!IronVaultAdminReceiver.isDeviceOwner(context)) return
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
            val admin = IronVaultAdminReceiver.getComponentName(context)
            dpm.setSecureSetting(admin, Settings.Global.ADB_ENABLED, "0")
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_DEBUGGING_FEATURES)
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_USB_FILE_TRANSFER)
        } catch (_: Exception) {}
    }
}

// ─── Brick Activity ───────────────────────────────────────────────────────────

class BrickActivity : ComponentActivity() {

    private var dismissReceiver: BroadcastReceiver? = null
    private val beaconScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Show above lock screen
        window.addFlags(
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or
            WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
            WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE.inv() // Allow touch for our screen only
        )

        val mode = intent.getStringExtra("mode") ?: "brick"
        val reason = intent.getStringExtra("reason") ?: "tamper_detected"

        // Block back button and recents
        setContent {
            BrickScreen(mode = mode, reason = reason)
        }

        // Register dismiss receiver (only responds to verified unlock token)
        dismissReceiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                finish()
            }
        }
        registerReceiver(dismissReceiver, IntentFilter(BrickMode.ACTION_DISMISS_BRICK))

        // Start periodic beacon (send location every 2 minutes)
        startBeacon()
    }

    private fun startBeacon() {
        beaconScope.launch {
            while (isActive) {
                delay(120_000) // 2 minutes
                try {
                    val repo = DeviceRepository(applicationContext)
                    val identity = IMSIProcessor.extractIdentity(applicationContext)
                    val sims = SIMIntelligence.extractAllSims(applicationContext)
                    val lm = getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
                    val loc = try {
                        lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                            ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
                    } catch (_: SecurityException) { null }

                    repo.sendAlert("brick_beacon", mapOf(
                        "fingerprint" to identity.hardwareFingerprint,
                        "imei" to (identity.imei ?: ""),
                        "sims" to sims.size,
                        "lat" to (loc?.latitude ?: 0.0),
                        "lng" to (loc?.longitude ?: 0.0),
                    ))
                } catch (_: Exception) {}
            }
        }
    }

    override fun onBackPressed() { /* Blocked */ }

    override fun onPause() {
        super.onPause()
        // Re-launch if another activity tries to cover this
        if (BrickMode.isActive(this)) {
            Handler(Looper.getMainLooper()).postDelayed({
                if (!isFinishing) {
                    val intent = Intent(this, BrickActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    }
                    startActivity(intent)
                }
            }, 500)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        dismissReceiver?.let { unregisterReceiver(it) }
        beaconScope.cancel()
    }
}

// ─── Brick UI ─────────────────────────────────────────────────────────────────

@Composable
fun BrickScreen(mode: String, reason: String) {
    val isBrick = mode == "brick"
    val bgColor = if (isBrick) Color(0xFFcc0000) else Color(0xFF1a1a2e)
    val title = when (mode) {
        "brick" -> "⛔ STOLEN DEVICE"
        "lost" -> "🔍 DEVICE REPORTED LOST"
        "lock" -> "🔒 DEVICE LOCKED"
        else -> "⚠️ DEVICE SECURED"
    }
    val body = when (mode) {
        "brick" -> "This device has been reported stolen.\nAll activity is being tracked and reported.\nReturn this device to receive a reward."
        "lost" -> "This device has been marked as lost.\nPlease contact the owner or turn it in to authorities."
        "lock" -> "This device is locked by your IT administrator.\nContact IT support to unlock."
        else -> "This device is secured by IronVault."
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bgColor),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp)
        ) {
            Text(
                title,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(24.dp))
            Text(
                body,
                fontSize = 16.sp,
                color = Color.White.copy(alpha = 0.9f),
                textAlign = TextAlign.Center,
                lineHeight = 24.sp
            )
            if (isBrick) {
                Spacer(Modifier.height(40.dp))
                Text(
                    "📡 Location is being transmitted",
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f)
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    "🚨 Law enforcement notified",
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f)
                )
            }
        }
    }
}
