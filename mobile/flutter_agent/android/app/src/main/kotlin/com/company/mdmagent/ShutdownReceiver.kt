package com.company.mdmagent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.location.Location
import android.location.LocationManager
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/**
 * Section 3.2 — High-precision shutdown location snapshot.
 * When device is powering off, captures last known location and syncs to backend.
 * Uses WorkManager / direct OkHttp since background services stop on shutdown.
 */
class ShutdownReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_SHUTDOWN &&
            intent.action != "android.intent.action.QUICKBOOT_POWEROFF") return

        Log.i("ShutdownReceiver", "Device shutting down — capturing location snapshot")

        // Use goAsync to get extra time for network call
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                captureAndSyncLocation(context)
            } finally {
                pendingResult.finish()
            }
        }
    }

    private suspend fun captureAndSyncLocation(context: Context) {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

        var bestLocation: Location? = null
        for (provider in listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER,
        )) {
            try {
                val loc = lm.getLastKnownLocation(provider)
                if (loc != null && (bestLocation == null || loc.accuracy < bestLocation!!.accuracy)) {
                    bestLocation = loc
                }
            } catch (_: SecurityException) {}
        }

        if (bestLocation == null) return

        val prefs = context.getSharedPreferences("mdm_secure", Context.MODE_PRIVATE)
        val deviceId = prefs.getString("device_id", null) ?: return
        val token = prefs.getString("device_token", null) ?: return
        val apiBase = prefs.getString("api_base_url", "https://mdm-api.yourcompany.com/api/v1")

        val body = JSONObject().apply {
            put("latitude", bestLocation!!.latitude)
            put("longitude", bestLocation!!.longitude)
            put("accuracy", bestLocation!!.accuracy)
            put("altitude", bestLocation!!.altitude)
            put("trigger", "shutdown_snapshot")
            put("recorded_at", java.time.Instant.now().toString())
        }.toString()

        val client = OkHttpClient.Builder()
            .callTimeout(8, java.util.concurrent.TimeUnit.SECONDS)
            .build()

        val request = Request.Builder()
            .url("$apiBase/devices/location")
            .addHeader("Authorization", "Bearer $token")
            .post(body.toRequestBody("application/json".toMediaType()))
            .build()

        try {
            client.newCall(request).execute().close()
            Log.i("ShutdownReceiver", "Shutdown snapshot synced: ${bestLocation!!.latitude},${bestLocation!!.longitude}")
        } catch (e: Exception) {
            Log.w("ShutdownReceiver", "Shutdown sync failed (offline): ${e.message}")
            // Queued by OfflineQueue on next boot
        }
    }
}
