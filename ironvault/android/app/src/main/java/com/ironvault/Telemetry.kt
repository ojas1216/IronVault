package com.ironvault

import android.content.Context
import androidx.work.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

object Telemetry {

    fun schedule(context: Context) {
        // Daily telemetry — every 24 hours
        val dailyWork = PeriodicWorkRequestBuilder<TelemetryWorker>(24, TimeUnit.HOURS)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "ironvault_telemetry",
            ExistingPeriodicWorkPolicy.KEEP,
            dailyWork
        )
    }

    fun scheduleImmediate(context: Context) {
        val work = OneTimeWorkRequestBuilder<TelemetryWorker>()
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .build()
        WorkManager.getInstance(context).enqueue(work)
    }
}

class TelemetryWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val prefs = applicationContext.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val deviceId = prefs.getString("device_id", "") ?: return@withContext Result.failure()

            // Gather full telemetry payload
            val identity = IMSIProcessor.extractIdentity(applicationContext)
            val sims = SIMIntelligence.extractAllSims(applicationContext)
            val hwComponents = HardwareTracker.readHardwareComponents(applicationContext)

            val lm = applicationContext.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
            val loc = try {
                lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                    ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
            } catch (_: SecurityException) { null }

            val payload = mapOf(
                "device_id" to deviceId,
                "hardware_fingerprint" to hwComponents.compositeFingerprint,
                "emmc_cid" to (hwComponents.emmcCid ?: ""),
                "wifi_mac" to (hwComponents.wifiMac ?: ""),
                "bt_mac" to (hwComponents.btMac ?: ""),
                "imei" to (identity.imei ?: ""),
                "imei2" to (identity.imei2 ?: ""),
                "serial" to (identity.serial ?: ""),
                "android_id" to identity.androidId,
                "soc_manufacturer" to hwComponents.socManufacturer,
                "soc_model" to hwComponents.socModel,
                "sim_count" to sims.size,
                "sims" to sims.map { sim ->
                    mapOf(
                        "slot" to sim.slot,
                        "iccid" to (sim.iccid ?: ""),
                        "carrier" to (sim.carrier ?: ""),
                        "country" to (sim.countryIso ?: ""),
                    )
                },
                "location" to if (loc != null) mapOf(
                    "lat" to loc.latitude,
                    "lng" to loc.longitude,
                    "accuracy" to loc.accuracy,
                ) else null,
                "checkin_timestamp" to System.currentTimeMillis(),
            )

            val repo = DeviceRepository(applicationContext)
            val response = repo.sendTelemetry(deviceId, payload)

            // Check if backend has flagged this device as stolen
            if (response.shouldBrick) {
                BrickMode.activate(applicationContext, "backend_marked_stolen")
            }

            // Store last checkin time
            prefs.edit()
                .putLong("last_telemetry_checkin", System.currentTimeMillis())
                .apply()

            Result.success()
        } catch (e: Exception) {
            // Will retry with exponential backoff
            Result.retry()
        }
    }
}

class ReEnrollmentWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val prefs = applicationContext.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val deviceName = prefs.getString("device_name", "") ?: return@withContext Result.failure()
            val ownerName = prefs.getString("owner_name", "") ?: return@withContext Result.failure()
            val ownerEmail = prefs.getString("owner_email", "") ?: return@withContext Result.failure()
            val department = prefs.getString("department", "") ?: return@withContext Result.failure()

            val repo = DeviceRepository(applicationContext)
            repo.enrollDevice(deviceName, ownerName, ownerEmail, department)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
