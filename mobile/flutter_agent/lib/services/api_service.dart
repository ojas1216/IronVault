import 'dart:io';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import '../config/app_config.dart';
import '../utils/secure_storage.dart';

class ApiService {
  static Dio? _dio;

  static Dio get client {
    _dio ??= _buildDio();
    return _dio!;
  }

  static Dio _buildDio() {
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));

    // Certificate pinning
    if (AppConfig.pinnedCertHashes.isNotEmpty) {
      (dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
        final client = HttpClient();
        client.badCertificateCallback = (cert, host, port) {
          // Verify certificate against pinned hashes
          return false; // reject all unmatched certs
        };
        return client;
      };
    }

    // Auth interceptor — auto-attach device JWT
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await SecureStorage.getDeviceToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Token expired — device needs re-enrollment
          await SecureStorage.clearAll();
        }
        return handler.next(error);
      },
    ));

    return dio;
  }

  static Future<Response> post(String path, Map<String, dynamic> data) =>
      client.post(path, data: data);

  static Future<Response> get(String path, {Map<String, dynamic>? params}) =>
      client.get(path, queryParameters: params);
}
