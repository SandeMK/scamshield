/// REST client for the ScamShield Cloud Scoring API (/api/v1, X-API-Key).
library;

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models.dart';

class ApiClient {
  static const defaultBaseUrl = 'http://10.0.2.2:8000'; // emulator -> host
  static const defaultApiKey = 'demo-key';

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
      {String? text, String? url, required String reportType}) async {
    final (base, key) = await _config();
    final resp = await http
        .post(Uri.parse('$base/api/v1/report'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': key},
            body: jsonEncode(
                {'text': text, 'url': url, 'report_type': reportType}))
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
}
