package com.company.mdmagent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Starts the MDM agent service on device boot.
 * Uses BOOT_COMPLETED — an official Android API, not a hack.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val serviceIntent = Intent(context, MDMForegroundService::class.java)
            context.startForegroundService(serviceIntent)
        }
    }
}
