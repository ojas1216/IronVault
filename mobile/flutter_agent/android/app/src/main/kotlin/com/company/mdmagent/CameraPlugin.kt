package com.company.mdmagent

import android.content.Context
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.util.concurrent.Executors

/**
 * Section 5.3 / 7.2 — Security camera capture using CameraX.
 * Captures front camera on SIM swap or remote command.
 * Disclosed in company policy — not hidden from users (foreground service notification visible).
 */
class CameraPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private val executor = Executors.newSingleThreadExecutor()

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, "com.company.mdmagent/camera")
        channel.setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "captureFront" -> {
                val outputPath = call.argument<String>("output_path") ?: run {
                    result.error("INVALID", "output_path required", null)
                    return
                }
                captureFromFrontCamera(outputPath, result)
            }
            else -> result.notImplemented()
        }
    }

    private fun captureFromFrontCamera(outputPath: String, result: MethodChannel.Result) {
        val providerFuture = ProcessCameraProvider.getInstance(context)
        providerFuture.addListener({
            try {
                val provider = providerFuture.get()

                val imageCapture = ImageCapture.Builder()
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()

                val cameraSelector = CameraSelector.Builder()
                    .requireLensFacing(CameraSelector.LENS_FACING_FRONT)
                    .build()

                // Bind to a headless lifecycle owner for background use
                val lifecycleOwner = HeadlessLifecycleOwner()
                provider.bindToLifecycle(lifecycleOwner, cameraSelector, imageCapture)

                val outputFile = File(outputPath)
                val outputOptions = ImageCapture.OutputFileOptions.Builder(outputFile).build()

                imageCapture.takePicture(
                    outputOptions,
                    executor,
                    object : ImageCapture.OnImageSavedCallback {
                        override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                            provider.unbindAll()
                            lifecycleOwner.stop()
                            result.success(outputPath)
                        }

                        override fun onError(exception: ImageCaptureException) {
                            Log.e("CameraPlugin", "Capture failed: ${exception.message}")
                            provider.unbindAll()
                            lifecycleOwner.stop()
                            result.error("CAPTURE_FAILED", exception.message, null)
                        }
                    }
                )
            } catch (e: Exception) {
                result.error("CAMERA_ERROR", e.message, null)
            }
        }, ContextCompat.getMainExecutor(context))
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        executor.shutdown()
    }
}

// Minimal LifecycleOwner for CameraX in background service
class HeadlessLifecycleOwner : androidx.lifecycle.LifecycleOwner {
    private val registry = androidx.lifecycle.LifecycleRegistry(this)
    init { registry.currentState = androidx.lifecycle.Lifecycle.State.STARTED }
    fun stop() { registry.currentState = androidx.lifecycle.Lifecycle.State.DESTROYED }
    override val lifecycle: androidx.lifecycle.Lifecycle get() = registry
}
