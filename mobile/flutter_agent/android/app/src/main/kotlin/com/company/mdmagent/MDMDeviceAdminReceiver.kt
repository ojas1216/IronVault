package com.company.mdmagent

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * Receives device admin events.
 * Required for DevicePolicyManager operations (lock, wipe, uninstall block).
 *
 * For Device Owner provisioning:
 *   adb shell dpm set-device-owner com.company.mdmagent/.MDMDeviceAdminReceiver
 *
 * In production use Android Enterprise Zero-touch or QR enrollment.
 */
class MDMDeviceAdminReceiver : DeviceAdminReceiver() {

    override fun onEnabled(context: Context, intent: Intent) {
        Log.i("MDMAdmin", "Device admin enabled")
        // Block own uninstall immediately on activation
        val dpm = getManager(context)
        val cn = getWho(context)
        dpm.setUninstallBlocked(cn, context.packageName, true)
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        return "Admin authorization is required to remove company security software. Contact IT."
    }

    override fun onDisabled(context: Context, intent: Intent) {
        Log.w("MDMAdmin", "Device admin disabled — this should require OTP authorization")
    }

}
