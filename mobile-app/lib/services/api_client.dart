/// REST client for the ScamShield Cloud Scoring API (/api/v1, X-API-Key).
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models.dart';

/// A non-2xx API response. [message] is safe to show to the user: the
/// server's own `detail` string when it sent one (the API's HTTPException
/// details are already written for people), otherwise a generic line by
/// status class. The raw body never reaches the UI.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  const ApiException(this.statusCode, this.message);

  factory ApiException.fromResponse(http.Response resp) {
    String? detail;
    try {
      final body = jsonDecode(resp.body);
      // FastAPI: HTTPException -> {"detail": "..."}; 422 validation ->
      // {"detail": [...]}, which is not user-facing, so it falls through.
      if (body is Map && body['detail'] is String) detail = body['detail'];
    } catch (_) {} // HTML error page from the host, empty body, etc.
    return ApiException(resp.statusCode, detail ?? _fallback(resp.statusCode));
  }

  static String _fallback(int status) {
    if (status == 401 || status == 403) {
      return 'This app is not authorised to use the ScamShield service';
    }
    if (status == 404) return 'Not found';
    if (status == 422) return 'Some details look invalid. Check and try again';
    if (status >= 500) return 'ScamShield is temporarily unavailable';
    return 'Request failed ($status)';
  }

  @override
  String toString() => message;
}

/// User-facing text for anything an [ApiClient] call can throw.
String friendlyError(Object e) {
  if (e is ApiException) return e.message;
  if (e is TimeoutException) return 'The server took too long to respond';
  if (e is SocketException || e is http.ClientException) {
    return "Can't reach ScamShield. Check your internet connection";
  }
  return 'Something went wrong';
}

class ApiClient {
  static const defaultBaseUrl = 'https://scamshield-api-4ywt.onrender.com';
  static const defaultApiKey = 'scamshield-api-key';

  Future<(String, String)> _config() async {
    // Saved overrides apply in debug builds only: release builds hide the
    // fields, so a stale saved value there could never be corrected.
    if (!kDebugMode) return (defaultBaseUrl, defaultApiKey);
    final prefs = await SharedPreferences.getInstance();
    return (
      prefs.getString('baseUrl') ?? defaultBaseUrl,
      prefs.getString('apiKey') ?? defaultApiKey,
    );
  }

  Future<ScoreResult> scoreSms(String text, String? sender) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/score/sms'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({'text': text, 'sender': sender}))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
    return ScoreResult.fromJson(jsonDecode(resp.body));
  }

  Future<void> report(
      {String? text,
      String? url,
      required String reportType,
      String? deviceId}) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/report'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({
              'text': text,
              'url': url,
              'report_type': reportType,
              'device_id': deviceId,
            }))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
  }

  Future<Map<String, dynamic>> health() async {
    final (base, _) = await _config();
    final resp = await http
        .get(Uri.parse('$base/api/v1/health'))
        .timeout(const Duration(seconds: 4));
    return jsonDecode(resp.body);
  }

  // ----- UC-13 Manage Profile & Notifications (FR-14/15/16) -----

  Future<Map<String, dynamic>> createOrUpdateProfile({
    required String deviceId,
    String? displayName,
    String? email,
    int? totalScans,
    int? totalReports,
  }) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/profile'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({
              'device_id': deviceId,
              'display_name': displayName,
              'email': email,
              'total_scans': totalScans,
              'total_reports': totalReports,
            }))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
    return jsonDecode(resp.body);
  }

  Future<Map<String, dynamic>?> getProfile(String deviceId) async {
    final (base, key) = await _config();
    final resp = await http
        .get(Uri.parse('$base/api/v1/profile/$deviceId'),
            headers: {'X-API-Key': key})
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode == 404) return null;
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
    return jsonDecode(resp.body);
  }

  Future<Map<String, dynamic>> updateNotificationPrefs({
    required String deviceId,
    required String alertThreshold,
    required bool retroactiveUpdates,
  }) async {
    final (base, key) = await _config();
    final resp = await http
        .patch(Uri.parse('$base/api/v1/profile/notifications'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({
              'device_id': deviceId,
              'alert_threshold': alertThreshold,
              'retroactive_updates': retroactiveUpdates,
            }))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
    return jsonDecode(resp.body);
  }

  Future<void> requestRecoveryCode(String email) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/profile/recovery/request'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({'email': email}))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
  }

  Future<Map<String, dynamic>> verifyRecoveryCode({
    required String email,
    required String code,
    required String deviceId,
  }) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/profile/recovery/verify'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode(
                {'email': email, 'code': code, 'device_id': deviceId}))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw ApiException.fromResponse(resp);
    }
    return jsonDecode(resp.body);
  }
}