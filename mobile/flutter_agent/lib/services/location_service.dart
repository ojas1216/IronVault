import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';

class LocationService {
  static Future<void> sendLocationUpdate() async {
    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) return;

      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.medium,
      );

      await ApiService.post('/devices/location', {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'accuracy': position.accuracy,
        'altitude': position.altitude,
        'speed': position.speed,
        'recorded_at': DateTime.now().toIso8601String(),
      });
    } catch (_) {}
  }
}
