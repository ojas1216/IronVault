package com.ironvault

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.telephony.SubscriptionInfo
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import kotlinx.coroutines.*

data class SimInfo(
    val slot: Int,
    val iccid: String?,
    val imsi: String?,
    val carrier: String?,
    val mcc: String?,
    val mnc: String?,
    val countryIso: String?,
    val isRoaming: Boolean,
    val phoneNumber: String?,
    val displayName: String?,
)

object SIMIntelligence {

    fun extractAllSims(context: Context): List<SimInfo> {
        val sm = context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as SubscriptionManager
        return try {
            val subs: List<SubscriptionInfo> = sm.activeSubscriptionInfoList ?: emptyList()
            subs.map { info ->
                val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
                val slotTm = tm.createForSubscriptionId(info.subscriptionId)
                SimInfo(
                    slot = info.simSlotIndex,
                    iccid = info.iccId,
                    imsi = getImsi(slotTm),
                    carrier = info.carrierName?.toString(),
                    mcc = info.mccString,
                    mnc = info.mncString,
                    countryIso = info.countryIso,
                    isRoaming = slotTm.isNetworkRoaming,
                    phoneNumber = info.number,
                    displayName = info.displayName?.toString(),
                )
            }
        } catch (_: SecurityException) { emptyList() }
    }

    private fun getImsi(tm: TelephonyManager): String? {
        return try {
            tm.subscriberId
        } catch (_: SecurityException) { null }
    }

    fun startMonitoring(context: Context) {
        val filter = IntentFilter().apply {
            addAction(TelephonyManager.ACTION_SIM_CARD_STATE_CHANGED)
            addAction(TelephonyManager.ACTION_PHONE_STATE_CHANGED)
            addAction("android.intent.action.SIM_STATE_CHANGED")
        }
        context.registerReceiver(SimStateReceiver, filter)
    }

    fun stopMonitoring(context: Context) {
        try { context.unregisterReceiver(SimStateReceiver) } catch (_: Exception) {}
    }

    private object SimStateReceiver : BroadcastReceiver() {
        private var lastKnownIccids: Set<String> = emptySet()

        override fun onReceive(context: Context, intent: Intent) {
            val currentSims = extractAllSims(context)
            val currentIccids = currentSims.mapNotNull { it.iccid }.toSet()

            // Detect changes
            if (lastKnownIccids.isNotEmpty()) {
                val removed = lastKnownIccids - currentIccids
                val inserted = currentIccids - lastKnownIccids

                if (removed.isNotEmpty() || inserted.isNotEmpty()) {
                    val eventType = when {
                        removed.isNotEmpty() && inserted.isNotEmpty() -> "swapped"
                        removed.isNotEmpty() -> "removed"
                        else -> "inserted"
                    }
                    onSimAnomaly(context, eventType, currentSims, removed, inserted)
                }
            }

            if (currentIccids.isNotEmpty()) {
                lastKnownIccids = currentIccids
            }
        }
    }

    private fun onSimAnomaly(
        context: Context,
        eventType: String,
        currentSims: List<SimInfo>,
        removed: Set<String>,
        inserted: Set<String>,
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            // 1. Get current location
            val location = getLastKnownLocation(context)

            // 2. Capture front camera
            val photoPath = try { CameraHelper.captureSecurityPhoto(context) } catch (_: Exception) { null }

            // 3. Alert backend
            try {
                val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
                val deviceId = prefs.getString("device_id", "") ?: return@launch
                val repo = DeviceRepository(context)

                repo.sendAlert("sim_anomaly", mapOf(
                    "event_type" to eventType,
                    "device_id" to deviceId,
                    "removed_iccids" to removed.toList(),
                    "inserted_iccids" to inserted.toList(),
                    "current_sims" to currentSims.map { sim ->
                        mapOf(
                            "slot" to sim.slot,
                            "iccid" to (sim.iccid ?: ""),
                            "carrier" to (sim.carrier ?: ""),
                            "mcc" to (sim.mcc ?: ""),
                            "mnc" to (sim.mnc ?: ""),
                            "country" to (sim.countryIso ?: ""),
                            "roaming" to sim.isRoaming,
                        )
                    },
                    "location" to location,
                    "photo_path" to (photoPath ?: ""),
                ))
            } catch (_: Exception) {
                // Queue for offline retry
                OfflineQueueHelper.enqueue(context, "sim_anomaly_alert", mapOf(
                    "event_type" to eventType,
                    "removed_iccids" to removed.toList(),
                    "inserted_iccids" to inserted.toList(),
                ))
            }

            // 4. Log to local DB
            val db = IronVaultDatabase.getInstance(context)
            db.tamperLogDao().insert(TamperLogEntry(
                event = "sim_$eventType:removed=${removed.joinToString()};inserted=${inserted.joinToString()}",
                timestamp = System.currentTimeMillis()
            ))
        }
    }

    private fun getLastKnownLocation(context: Context): Map<String, Double>? {
        return try {
            val lm = context.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
            val loc = lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
            loc?.let { mapOf("lat" to it.latitude, "lng" to it.longitude, "acc" to it.accuracy.toDouble()) }
        } catch (_: Exception) { null }
    }
}
