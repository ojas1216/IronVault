package com.ironvault

import android.app.admin.DeviceAdminReceiver
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.UserHandle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class IronVaultAdminReceiver : DeviceAdminReceiver() {

    override fun onEnabled(context: Context, intent: Intent) {
        logTamper(context, "device_admin_enabled")
        // Apply device policies immediately
        applyPolicies(context)
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        // Log the attempt
        logTamper(context, "admin_disable_requested")
        // Alert backend immediately
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val repo = DeviceRepository(context)
                repo.sendAlert("admin_disable_attempt", mapOf(
                    "message" to "Employee attempted to disable Device Admin"
                ))
            } catch (_: Exception) {}
        }
        // Return warning message — Android will show this in confirmation dialog
        return "⚠️ This device is managed by your company. " +
               "Disabling requires administrator authorization."
    }

    override fun onDisabled(context: Context, intent: Intent) {
        logTamper(context, "device_admin_disabled")
        // Attempt to re-register
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val repo = DeviceRepository(context)
                repo.sendAlert("admin_disabled", mapOf(
                    "severity" to "CRITICAL",
                    "message" to "Device admin was disabled — protection removed"
                ))
            } catch (_: Exception) {}
        }
        // Schedule re-enrollment attempt
        scheduleReEnrollment(context)
    }

    override fun onPasswordFailed(context: Context, intent: Intent, user: UserHandle) {
        logTamper(context, "password_attempt_failed")
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val failures = dpm.currentFailedPasswordAttempts
        if (failures >= 5) {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val repo = DeviceRepository(context)
                    repo.sendAlert("repeated_password_failures", mapOf(
                        "attempts" to failures,
                        "severity" to "HIGH"
                    ))
                } catch (_: Exception) {}
            }
        }
    }

    override fun onPasswordSucceeded(context: Context, intent: Intent, user: UserHandle) {
        logTamper(context, "password_unlocked")
    }

    override fun onLockTaskModeEntering(context: Context, intent: Intent, pkg: String) {
        logTamper(context, "lock_task_entering:$pkg")
    }

    override fun onLockTaskModeExiting(context: Context, intent: Intent) {
        logTamper(context, "lock_task_exiting")
    }

    private fun applyPolicies(context: Context) {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(context, IronVaultAdminReceiver::class.java)

        try {
            // Prevent uninstall
            dpm.setUninstallBlocked(admin, context.packageName, true)
            // Require device encryption
            dpm.setStorageEncryption(admin, true)
            // Max password attempts before wipe (10 attempts)
            dpm.setMaximumFailedPasswordsForWipe(admin, 10)
            // Screen lock timeout (5 minutes)
            dpm.setMaximumTimeToLock(admin, 5 * 60 * 1000L)
        } catch (e: SecurityException) {
            // Device Owner privileges required for some policies
        }

        // Apply FRP if Device Owner
        if (dpm.isDeviceOwnerApp(context.packageName)) {
            applyDeviceOwnerPolicies(context, dpm, admin)
        }
    }

    private fun applyDeviceOwnerPolicies(
        context: Context,
        dpm: DevicePolicyManager,
        admin: ComponentName
    ) {
        try {
            // Block factory reset
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_FACTORY_RESET)
            // Block safe mode boot
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_SAFE_BOOT)
            // Block adding non-company accounts
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_ADD_USER)
            // Block USB debugging
            dpm.addUserRestriction(admin, android.os.UserManager.DISALLOW_DEBUGGING_FEATURES)
            // Disable ADB
            dpm.setSecureSetting(admin, android.provider.Settings.Global.ADB_ENABLED, "0")
        } catch (e: SecurityException) {
            logTamper(context, "policy_apply_failed:${e.message}")
        }
    }

    private fun scheduleReEnrollment(context: Context) {
        val workRequest = androidx.work.OneTimeWorkRequestBuilder<ReEnrollmentWorker>()
            .setInitialDelay(30, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        androidx.work.WorkManager.getInstance(context).enqueue(workRequest)
    }

    private fun logTamper(context: Context, event: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val db = IronVaultDatabase.getInstance(context)
                db.tamperLogDao().insert(TamperLogEntry(
                    event = event,
                    timestamp = System.currentTimeMillis()
                ))
            } catch (_: Exception) {}
        }
    }

    companion object {
        fun getComponentName(context: Context) =
            ComponentName(context, IronVaultAdminReceiver::class.java)

        fun isAdminActive(context: Context): Boolean {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            return dpm.isAdminActive(getComponentName(context))
        }

        fun isDeviceOwner(context: Context): Boolean {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            return dpm.isDeviceOwnerApp(context.packageName)
        }
    }
}
