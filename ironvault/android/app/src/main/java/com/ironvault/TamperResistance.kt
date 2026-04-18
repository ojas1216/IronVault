package com.ironvault

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.wifi.WifiManager
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import kotlinx.coroutines.*

object TamperResistance {

    private var airplaneModeReceiver: BroadcastReceiver? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun startAllProtections(context: Context) {
        blockAirplaneMode(context)
        monitorPowerMenu(context)
        monitorAppInstallation(context)
    }

    fun stopAllProtections(context: Context) {
        try {
            airplaneModeReceiver?.let { context.unregisterReceiver(it) }
        } catch (_: Exception) {}
        scope.cancel()
    }

    // Block airplane mode — re-enable radio as soon as airplane mode is toggled
    private fun blockAirplaneMode(context: Context) {
        val filter = IntentFilter(Intent.ACTION_AIRPLANE_MODE_CHANGED)
        airplaneModeReceiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                val enabled = intent.getBooleanExtra("state", false)
                if (enabled) {
                    logTamper(context, "airplane_mode_enabled_blocked")
                    scope.launch {
                        delay(500) // Brief delay to let system process
                        restoreConnectivity(ctx)
                        alertBackend(ctx, "airplane_mode_blocked")
                    }
                }
            }
        }
        context.registerReceiver(airplaneModeReceiver, filter)
    }

    private fun restoreConnectivity(context: Context) {
        // Re-enable WiFi
        try {
            val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            if (!wm.isWifiEnabled) {
                @Suppress("DEPRECATION")
                wm.isWifiEnabled = true
            }
        } catch (_: Exception) {}

        // Re-enable mobile data via Device Policy Manager if Device Owner
        if (IronVaultAdminReceiver.isDeviceOwner(context)) {
            try {
                val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
                val admin = IronVaultAdminReceiver.getComponentName(context)
                // Clear airplane mode global setting
                dpm.setGlobalSetting(admin, Settings.Global.AIRPLANE_MODE_ON, "0")
                // Re-enable mobile data
                dpm.setGlobalSetting(admin, "mobile_data", "1")
            } catch (_: Exception) {}
        }
    }

    private fun monitorPowerMenu(context: Context) {
        // This is limited on Android without root.
        // Best-effort: if screen goes off unexpectedly, lock device and re-activate
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_USER_PRESENT)
        }
        context.registerReceiver(object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                if (intent.action == Intent.ACTION_SCREEN_OFF) {
                    logTamper(context, "screen_off")
                }
            }
        }, filter)
    }

    private fun monitorAppInstallation(context: Context) {
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_PACKAGE_ADDED)
            addAction(Intent.ACTION_PACKAGE_REPLACED)
            addDataScheme("package")
        }
        context.registerReceiver(object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                val pkg = intent.data?.schemeSpecificPart ?: return
                if (isSuspiciousApp(pkg)) {
                    logTamper(context, "suspicious_app_installed:$pkg")
                    scope.launch { alertBackend(context, "suspicious_app:$pkg") }
                }
            }
        }, filter)
    }

    private fun isSuspiciousApp(packageName: String): Boolean {
        val suspiciousPatterns = listOf(
            "frida", "xposed", "substrate", "cydia", "lucky_patcher",
            "freedom", "gamekiller", "cheatengine", "gameguardian"
        )
        return suspiciousPatterns.any { packageName.contains(it, ignoreCase = true) }
    }

    private fun logTamper(context: Context, event: String) {
        scope.launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = event,
                    timestamp = System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    private suspend fun alertBackend(context: Context, event: String) {
        try {
            val repo = DeviceRepository(context)
            repo.sendAlert("tamper_event", mapOf(
                "event" to event,
                "timestamp" to System.currentTimeMillis()
            ))
        } catch (_: Exception) {}
    }
}

// ─── Boot Receiver ────────────────────────────────────────────────────────────

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_LOCKED_BOOT_COMPLETED) {
            // Start tracking service after boot
            TrackingService.startService(context)
            // Verify hardware fingerprint
            CoroutineScope(Dispatchers.IO).launch {
                SecureBoot.verifyOnBoot(context)
            }
        }
    }
}

// ─── Service Restart Receiver ─────────────────────────────────────────────────

class ServiceRestartReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == TrackingService.ACTION_RESTART_SERVICE) {
            TrackingService.startService(context)
        }
    }
}

// ─── SMS Receiver ────────────────────────────────────────────────────────────

class SMSReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == "android.provider.Telephony.SMS_RECEIVED") {
            SMSCommandParser.parseSMS(context, intent)
        }
    }
}

// ─── Shutdown Receiver ───────────────────────────────────────────────────────

class ShutdownReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_SHUTDOWN) return
        // Use goAsync to get up to 10 seconds of execution time
        val result = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val lm = context.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
                val loc = lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                    ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)

                if (loc != null) {
                    val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
                    val deviceId = prefs.getString("device_id", "") ?: return@launch
                    val serverUrl = prefs.getString("server_url", "") ?: return@launch

                    // Direct OkHttp call — no Retrofit layer needed
                    val client = okhttp3.OkHttpClient.Builder()
                        .connectTimeout(5, java.util.concurrent.TimeUnit.SECONDS)
                        .readTimeout(5, java.util.concurrent.TimeUnit.SECONDS)
                        .build()
                    val body = okhttp3.RequestBody.create(
                        okhttp3.MediaType.parse("application/json"),
                        """{"device_id":"$deviceId","lat":${loc.latitude},"lng":${loc.longitude},"event":"shutdown"}"""
                    )
                    val request = okhttp3.Request.Builder()
                        .url("$serverUrl/devices/shutdown-location")
                        .post(body)
                        .build()
                    runCatching { client.newCall(request).execute() }
                }
            } finally {
                result.finish()
            }
        }
    }
}
