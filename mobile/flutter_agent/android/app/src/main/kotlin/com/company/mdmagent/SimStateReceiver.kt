package com.company.mdmagent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log
import io.flutter.plugin.common.EventChannel

class SimStateReceiver : BroadcastReceiver {

    private var eventSink: EventChannel.EventSink? = null

    constructor(sink: EventChannel.EventSink?) : super() {
        this.eventSink = sink
    }

    constructor() : super()

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action !in SIM_ACTIONS) return

        // Legacy broadcast uses "simStatus" extra; newer broadcasts use "android.telephony.extra.SIM_STATE"
        val state = intent.getIntExtra("simStatus",
            intent.getIntExtra("android.telephony.extra.SIM_STATE", -1))
        val slotIndex = intent.getIntExtra("simSlotIndex", 0)

        // SIM_STATE_ABSENT=1, SIM_STATE_PRESENT=11 (API 26+)
        val eventType = when (state) {
            11 -> "inserted"
            1  -> "removed"
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

    companion object {
        private val SIM_ACTIONS = setOf(
            "android.telephony.action.SIM_CARD_STATE_CHANGED",
            "android.telephony.action.SUBSCRIPTION_CARRIER_IDENTITY_CHANGED",
            "android.intent.action.SIM_STATE_CHANGED",
        )

        private var receiver: SimStateReceiver? = null

        fun register(context: Context, sink: EventChannel.EventSink?) {
            receiver = SimStateReceiver(sink)
            val filter = IntentFilter().apply {
                SIM_ACTIONS.forEach { addAction(it) }
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
