class AppConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://mdm-api.yourcompany.com/api/v1',
  );

  static const String enrollmentCode = String.fromEnvironment(
    'ENROLLMENT_CODE',
    defaultValue: 'COMPANY_ENROLL_2024_SECURE',
  );

  // Heartbeat interval (seconds)
  static const int heartbeatInterval = 30;

  // Location update interval (seconds)
  static const int locationInterval = 300; // 5 minutes

  // App usage sync interval (seconds)
  static const int appUsageSyncInterval = 3600; // 1 hour

  // Certificate pinning SHA-256 hash of server certificate
  static const List<String> pinnedCertHashes = [
    // Add your server cert SHA-256 here
    // 'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
  ];
}
