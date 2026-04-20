package com.company.mdmagent

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        flutterEngine.plugins.add(DevicePolicyPlugin())
        flutterEngine.plugins.add(AlarmPlugin())
        flutterEngine.plugins.add(CameraPlugin())
        flutterEngine.plugins.add(SimPlugin())
        flutterEngine.plugins.add(DeviceIdentityPlugin())
        flutterEngine.plugins.add(TamperPlugin())
        flutterEngine.plugins.add(UWBPlugin())
    }
}
