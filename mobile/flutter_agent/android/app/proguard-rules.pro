##──────────────────────────────────────────────────────────────────────────
##  ProGuard / R8 Rules — Company MDM Agent
##  Purpose: Obfuscate code so company developers cannot reverse-engineer it.
##  Applied automatically on release builds.
##──────────────────────────────────────────────────────────────────────────

# ── Aggressive shrink + obfuscate ────────────────────────────────────────
-optimizationpasses 7
-allowaccessmodification
-repackageclasses 'x'                       # flatten all packages into 'x'
-overloadaggressively
-useuniqueclassmembernames
-adaptclassstrings
-adaptresourcefilenames
-adaptresourcefilecontents **.properties,**.xml

# ── Rename everything (including package names) ─────────────────────────
-obfuscationdictionary obfuscation_dict.txt
-classobfuscationdictionary obfuscation_dict.txt
-packageobfuscationdictionary obfuscation_dict.txt

# ── String encryption (via R8's string obfuscation) ──────────────────────
# R8 handles this automatically in full-mode; additionally enable:
-optimizations code/simplification/string

# ── Keep only what Android framework requires ────────────────────────────
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable    # remove in production for max obfuscation
-keepattributes Signature
-keepattributes Exceptions

# ── Android system components — must keep exact names ────────────────────
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.app.admin.DeviceAdminReceiver
-keep public class * extends android.content.ContentProvider
-keep class com.company.mdmagent.MDMDeviceAdminReceiver { *; }
-keep class com.company.mdmagent.BootReceiver { *; }
-keep class com.company.mdmagent.ShutdownReceiver { *; }
-keep class com.company.mdmagent.SimStateReceiver { *; }
-keep class com.company.mdmagent.WatchdogService { *; }

# ── Flutter plugin bridge — keep method channel names ────────────────────
-keep class io.flutter.** { *; }
-keep class io.flutter.plugin.** { *; }
-keepclassmembers class * {
    @io.flutter.plugin.common.MethodChannel.MethodCallHandler *;
}

# ── Firebase / FCM ───────────────────────────────────────────────────────
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.firebase.**

# ── CameraX ──────────────────────────────────────────────────────────────
-keep class androidx.camera.** { *; }
-dontwarn androidx.camera.**

# ── OkHttp (used in ShutdownReceiver) ───────────────────────────────────
-dontwarn okhttp3.**
-dontwarn okio.**

# ── Remove all logging in release ────────────────────────────────────────
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
    public static int w(...);
    public static int e(...);
}
# Also strip Timber
-assumenosideeffects class timber.log.Timber {
    public static *** v(...);
    public static *** d(...);
    public static *** i(...);
    public static *** w(...);
    public static *** e(...);
}

# ── Prevent decompilers seeing class structure ────────────────────────────
-keepclassmembers,allowobfuscation class * {
    @androidx.annotation.Keep *;
}

# ── Remove source file names from stack traces ────────────────────────────
-renamesourcefileattribute SourceFile
