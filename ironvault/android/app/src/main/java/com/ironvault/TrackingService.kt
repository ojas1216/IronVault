package com.ironvault

import android.app.*
import android.content.Context
import android.content.Intent
import android.location.Location
import android.net.ConnectivityManager
import android.net.wifi.WifiManager
import android.os.IBinder
import android.os.Looper
import android.telephony.TelephonyManager
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import kotlinx.coroutines.*

class TrackingService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private var lastLocation: Location? = null
    private var syncJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        setupLocationUpdates()
        startSyncLoop()
    }

    private fun setupLocationUpdates() {
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 15_000L)
            .setMinUpdateIntervalMillis(10_000L)
            .setMaxUpdateDelayMillis(30_000L)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val loc = result.lastLocation ?: return
                lastLocation = loc
                scope.launch {
                    saveLocationLocally(loc)
                    if (isOnline()) syncPendingLocations()
                }
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(request, locationCallback, Looper.getMainLooper())
        } catch (e: SecurityException) {
            // Permission not granted — log and rely on network fallback
            startNetworkLocationFallback()
        }
    }

    private fun startNetworkLocationFallback() {
        scope.launch {
            while (isActive) {
                try {
                    val networkLoc = getNetworkLocation()
                    if (networkLoc != null) {
                        saveLocationLocally(networkLoc)
                        if (isOnline()) syncPendingLocations()
                    }
                } catch (_: Exception) {}
                delay(60_000)
            }
        }
    }

    private fun getNetworkLocation(): Location? {
        val locationManager = getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
        return try {
            val gps = locationManager.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
            val network = locationManager.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
            val passive = locationManager.getLastKnownLocation(android.location.LocationManager.PASSIVE_PROVIDER)
            // Return most accurate / most recent
            listOfNotNull(gps, network, passive).maxByOrNull { it.time }
        } catch (e: SecurityException) { null }
    }

    private suspend fun saveLocationLocally(loc: Location) {
        val db = IronVaultDatabase.getInstance(this)
        db.locationDao().insert(LocationRecord(
            latitude = loc.latitude,
            longitude = loc.longitude,
            accuracy = loc.accuracy,
            altitude = loc.altitude,
            speed = loc.speed,
            provider = loc.provider ?: "unknown",
            timestamp = loc.time,
            synced = false
        ))
        // Keep only last 1000 records locally
        db.locationDao().pruneOldRecords(1000)
    }

    private suspend fun syncPendingLocations() {
        val db = IronVaultDatabase.getInstance(this)
        val pending = db.locationDao().getUnsynced(50)
        if (pending.isEmpty()) return

        try {
            val repo = DeviceRepository(this)
            val prefs = getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val deviceId = prefs.getString("device_id", "") ?: return

            repo.sendHeartbeat(deviceId, pending)
            db.locationDao().markSynced(pending.map { it.id })
        } catch (_: Exception) {
            // Will retry next cycle
        }
    }

    private fun startSyncLoop() {
        syncJob = scope.launch {
            while (isActive) {
                delay(900_000) // 15 minutes
                if (isOnline()) syncPendingLocations()
                checkForPendingCommands()
            }
        }
    }

    private suspend fun checkForPendingCommands() {
        try {
            val prefs = getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
            val deviceId = prefs.getString("device_id", "") ?: return
            val repo = DeviceRepository(this)
            val commands = repo.getPendingCommands(deviceId)
            commands.forEach { cmd ->
                RemoteCommandProcessor.execute(this, cmd)
            }
        } catch (_: Exception) {}
    }

    private fun isOnline(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val net = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(net) ?: return false
        return caps.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "System Health",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "System health monitoring service"
            setShowBadge(false)
        }
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("System Health")
            .setContentText("Monitoring device health...")
            .setSmallIcon(android.R.drawable.ic_menu_manage)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Restart service when app is force-stopped
        val restartIntent = Intent(applicationContext, TrackingService::class.java)
        val pendingIntent = PendingIntent.getService(
            applicationContext, 1, restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.set(
            AlarmManager.ELAPSED_REALTIME,
            android.os.SystemClock.elapsedRealtime() + 1000,
            pendingIntent
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocationClient.removeLocationUpdates(locationCallback)
        scope.cancel()
        // Restart via broadcast
        sendBroadcast(Intent(ACTION_RESTART_SERVICE))
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "system_health"
        const val ACTION_RESTART_SERVICE = "com.ironvault.RESTART_SERVICE"

        fun startService(context: Context) {
            val intent = Intent(context, TrackingService::class.java)
            context.startForegroundService(intent)
        }

        fun stopService(context: Context) {
            context.stopService(Intent(context, TrackingService::class.java))
        }
    }
}
