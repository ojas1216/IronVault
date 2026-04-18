package com.company.mdmagent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.telephony.TelephonyManager
import android.util.Log
import io.flutter.plugin.common.EventChannel

/**
 * Section 5.2 — SIM Lifecycle Monitoring
 * Detects SIM inserted / removed / swapped events.
 * Fires into Flutter EventChannel for anomaly pipeline.
 */
class SimStateReceiver : BroadcastReceiver() {

    private var eventSink: EventChannel.EventSink? = null

    constructor(sink: EventChannel.EventSink?) {
        this.eventSink = sink
    }

    constructor() // required for BroadcastReceiver

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return

        when (action) {
            TelephonyManager.ACTION_SIM_CARD_STATE_CHANGED,
            TelephonyManager.ACTION_SUBSCRIPTION_CARRIER_IDENTITY_CHANGED -> {
                val state = intent.getIntExtra(
                    TelephonyManager.EXTRA_SIM_STATE,
                    TelephonyManager.SIM_STATE_UNKNOWN,
                )
                val slotIndex = intent.getIntExtra("simSlotIndex", 0)

                val eventType = when (state) {
                    TelephonyManager.SIM_STATE_PRESENT -> "inserted"
                    TelephonyManager.SIM_STATE_ABSENT -> "removed"
                    else -> "changed"
                }

                Log.w("SIMMonitor", "SIM event: $eventType on slot $slotIndex")

                eventSink?.success(mapOf(
                    "event_type" to eventType,
                    "slot_index" to slotIndex,
                    "sim_state" to state,
                    "timestamp" to System.currentTimeMillis(),
                ))
            }
        }
    }

    companion object {
        private var receiver: SimStateReceiver? = null

        fun register(context: Context, sink: EventChannel.EventSink?) {
            receiver = SimStateReceiver(sink)
            val filter = IntentFilter().apply {
                addAction(TelephonyManager.ACTION_SIM_CARD_STATE_CHANGED)
                addAction(TelephonyManager.ACTION_SUBSCRIPTION_CARRIER_IDENTITY_CHANGED)
                addAction("android.intent.action.SIM_STATE_CHANGED")
            }
            context.registerReceiver(receiver, filter)
        }

        fun unregister(context: Context) {
            receiver?.let {
                try { context.unregisterReceiver(it) } catch (_: Exception) {}
                receiver = null
            }
        }
    }
}
