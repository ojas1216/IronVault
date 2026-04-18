package com.company.mdmagent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import kotlinx.coroutines.*

/**
 * Section 6.5 — Anti-force-stop service monitor.
 * Runs as a persistent foreground service.
 * Periodically checks if the main MDM service is alive and restarts it if not.
 * The OS cannot kill a foreground service without user action.
 */
class WatchdogService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onCreate() {
        super.onCreate()
        startForeground(889, buildNotification())
        startWatchLoop()
    }

    private fun startWatchLoop() {
        scope.launch {
            while (isActive) {
                delay(15_000) // check every 15 seconds
                ensureMainServiceRunning()
            }
        }
    }

    private fun ensureMainServiceRunning() {
        val manager = getSystemService(ACTIVITY_SERVICE) as android.app.ActivityManager
        val running = manager.getRunningServices(50).any {
            it.service.className == MDMForegroundService::class.java.name
        }
        if (!running) {
            Log.w("Watchdog", "MDM service not running — restarting")
            val intent = Intent(this, MDMForegroundService::class.java)
            startForegroundService(intent)
        }
    }

    private fun buildNotification(): Notification {
        val channelId = "watchdog_channel"
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(channelId, "Device Security", NotificationManager.IMPORTANCE_MIN)
            )
        }
        return Notification.Builder(this, channelId)
            .setContentTitle("Device Security")
            .setContentText("Security monitoring active")
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int =
        START_STICKY // restart automatically if killed

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        // Self-restart if destroyed
        sendBroadcast(Intent(this, BootReceiver::class.java).apply {
            action = Intent.ACTION_BOOT_COMPLETED
        })
        super.onDestroy()
    }
}
