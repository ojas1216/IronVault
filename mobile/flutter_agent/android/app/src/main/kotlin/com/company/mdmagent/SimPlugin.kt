package com.company.mdmagent

import android.content.Context
import android.telephony.TelephonyManager
import android.telephony.SubscriptionManager
import android.os.Build
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

class SimPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var methodChannel: MethodChannel
    private lateinit var eventChannel: EventChannel
    private var eventSink: EventChannel.EventSink? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext

        methodChannel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/sim")
        methodChannel.setMethodCallHandler(this)

        eventChannel = EventChannel(binding.binaryMessenger, "com.company.mdmagent/sim_events")
        eventChannel.setStreamHandler(SimEventStreamHandler(context))
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "getSimMetadata" -> result.success(extractSimMetadata())
            else -> result.notImplemented()
        }
    }

    private fun extractSimMetadata(): Map<String, Any?> {
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        val sm = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1)
            context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as SubscriptionManager
        else null

        val slots = mutableListOf<Map<String, Any?>>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1 && sm != null) {
            val subscriptions = sm.activeSubscriptionInfoList ?: emptyList()
            for (sub in subscriptions) {
                val slotTm = tm.createForSubscriptionId(sub.subscriptionId)
                slots.add(mapOf(
                    "slot_index" to sub.simSlotIndex,
                    "iccid" to sub.iccId,                         // 5.1 ICCID
                    "carrier_name" to sub.carrierName?.toString(), // 5.1 Carrier
                    "mcc" to sub.mcc.toString(),                   // 5.1 MCC
                    "mnc" to sub.mnc.toString(),                   // 5.1 MNC
                    "country_iso" to sub.countryIso,               // 5.1 Country
                    "phone_number" to sub.number,                  // 5.1 Phone number
                    "display_name" to sub.displayName?.toString(),
                    "is_roaming" to (slotTm.isNetworkRoaming),    // 5.1 Roaming
                    "network_operator_name" to slotTm.networkOperatorName,
                ))
            }
        } else {
            // Legacy single-SIM fallback
            slots.add(mapOf(
                "slot_index" to 0,
                "carrier_name" to tm.networkOperatorName,
                "country_iso" to tm.networkCountryIso,
                "phone_number" to tm.line1Number,
                "is_roaming" to tm.isNetworkRoaming,
            ))
        }

        return mapOf(
            "slots" to slots,
            "sim_count" to slots.size,
            "timestamp" to System.currentTimeMillis(),
        )
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        methodChannel.setMethodCallHandler(null)
    }
}

class SimEventStreamHandler(private val context: Context) : EventChannel.StreamHandler {
    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        SimStateReceiver.register(context, events)
    }

    override fun onCancel(arguments: Any?) {
        SimStateReceiver.unregister(context)
    }
}
