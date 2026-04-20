import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

/// Section 5.3 / 7.2 — Security camera capture
/// Captures front camera image on SIM swap or remote command.
/// Disclosed in company device policy — not hidden surveillance.
class CameraService {
  static const _channel = MethodChannel('com.company.mdmagent/camera');

  /// Capture front-facing camera photo using CameraX in background.
  /// Returns local file path or null on failure.
  static Future<String?> captureSecurityPhoto({required String trigger}) async {
    try {
      final dir = await getTemporaryDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final outputPath = '${dir.path}/security_$trigger\_$timestamp.jpg';

      final result = await _channel.invokeMethod<String>('captureFront', {
        'output_path': outputPath,
        'trigger': trigger,
      });
      return result;
    } catch (e) {
      return null;
    }
  }

  /// Upload captured security photo to backend
  static Future<bool> uploadPhoto(String filePath, String commandId) async {
    try {
      // Upload via multipart — use separate upload endpoint
      await _channel.invokeMethod('uploadSecurityPhoto', {
        'file_path': filePath,
        'command_id': commandId,
      });
      // Clean up local file after upload
      final file = File(filePath);
      if (await file.exists()) await file.delete();
      return true;
    } catch (_) {
      return false;
    }
  }
}
