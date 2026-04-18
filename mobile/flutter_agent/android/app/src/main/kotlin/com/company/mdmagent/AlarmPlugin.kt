package com.company.mdmagent

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.os.Build
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.util.Timer
import java.util.TimerTask

/** Section 7.2 — Remote alarm trigger */
class AlarmPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private var mediaPlayer: MediaPlayer? = null
    private var alarmTimer: Timer? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/alarm")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "triggerAlarm" -> {
                val duration = call.argument<Int>("duration_seconds") ?: 30
                triggerAlarm(duration)
                result.success(null)
            }
            "stopAlarm" -> {
                stopAlarm()
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    private fun triggerAlarm(durationSeconds: Int) {
        // Force maximum volume
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.setStreamVolume(
            AudioManager.STREAM_ALARM,
            audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM),
            0,
        )

        // Play alarm ringtone
        mediaPlayer?.release()
        val alarmUri = android.provider.Settings.System.DEFAULT_ALARM_ALERT_URI
        mediaPlayer = MediaPlayer().apply {
            setAudioAttributes(AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build())
            setDataSource(context, alarmUri)
            isLooping = true
            prepare()
            start()
        }

        // Vibrate
        val pattern = longArrayOf(0, 500, 200, 500)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vm.defaultVibrator.vibrate(VibrationEffect.createWaveform(pattern, 0))
        } else {
            @Suppress("DEPRECATION")
            val v = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            v.vibrate(pattern, 0)
        }

        // Auto-stop after duration
        alarmTimer?.cancel()
        alarmTimer = Timer().also {
            it.schedule(object : TimerTask() {
                override fun run() { stopAlarm() }
            }, durationSeconds * 1000L)
        }
    }

    private fun stopAlarm() {
        alarmTimer?.cancel()
        mediaPlayer?.apply { stop(); release() }
        mediaPlayer = null
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? android.os.VibratorManager)
                ?.defaultVibrator?.cancel()
        } else {
            @Suppress("DEPRECATION")
            (context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)?.cancel()
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        stopAlarm()
        channel.setMethodCallHandler(null)
    }
}
