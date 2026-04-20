package com.company.mdmagent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder

class MDMForegroundService : Service() {

    override fun onCreate() {
        super.onCreate()
        startForeground(888, buildNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildNotification(): Notification {
        val channelId = "mdm_service_channel"
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(channelId, "Device Security", NotificationManager.IMPORTANCE_MIN)
            )
        }
        return Notification.Builder(this, channelId)
            .setContentTitle("Device Security Active")
            .setContentText("Company device monitoring is running")
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .build()
    }
}
