/// REST client for the ScamShield Cloud Scoring API (/api/v1, X-API-Key).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models.dart';

class ApiClient {
  static const defaultBaseUrl = 'https://scamshield-api-4ywt.onrender.com';
  static const defaultApiKey = 'scamshield-api-key';

  Future<(String, String)> _config() async {
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
    }
    return jsonDecode(resp.body);
  }

  Future<Map<String, dynamic>> updateNotificationPrefs({
    required String deviceId,
    required String alertThreshold,
    required bool retroactiveUpdates,
    required bool reportOutcomes,
    required String digestFrequency,
  }) async {
    final (base, key) = await _config();
    final resp = await http
        .patch(Uri.parse('$base/api/v1/profile/notifications'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode({
              'device_id': deviceId,
              'alert_threshold': alertThreshold,
              'retroactive_updates': retroactiveUpdates,
              'report_outcomes': reportOutcomes,
              'digest_frequency': digestFrequency,
            }))
        .timeout(const Duration(seconds: 6));
    if (resp.statusCode != 200) {
      throw Exception('API ${resp.statusCode}: ${resp.body}');
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
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
      throw Exception('API ${resp.statusCode}: ${resp.body}');
    }
    return jsonDecode(resp.body);
  }
}