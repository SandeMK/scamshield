/// Central scan pipeline + persistent store.
///
/// Every message (real SMS or simulated) flows through [process]:
///   1. FR-10 local heuristics -> instant provisional result
///   2. Cloud hybrid scoring -> final result
///   3. NFR-08 offline fallback: keep local result, mark cloud offline
library;

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models.dart';
import 'api_client.dart';
import 'local_rules.dart';

class ScanStore extends ChangeNotifier {
  ScanStore._();
  static final instance = ScanStore._();

  final api = ApiClient();
  final List<Scan> scans = [];
  int reportsSent = 0;
  bool loaded = false;

  Future<void> load() async {
    if (loaded) return;
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('scans');
    if (raw != null) {
      scans
        ..clear()
        ..addAll((jsonDecode(raw) as List).map((e) => Scan.fromJson(e)));
    }
    reportsSent = prefs.getInt('reportsSent') ?? 0;
    loaded = true;
    notifyListeners();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    final recent = scans.take(200).toList(); // keep storage bounded
    await prefs.setString(
        'scans', jsonEncode(recent.map((s) => s.toJson()).toList()));
    await prefs.setInt('reportsSent', reportsSent);
  }

  /// Full pipeline for one message. Returns the scan (already in the list).
  Future<Scan> process(String text, String sender, String source) async {
    final local = runLocalRules(text);
    final scan = Scan(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      text: text,
      sender: sender,
      timestamp: DateTime.now(),
      source: source,
      localScore: local.score,
      localFlags: local.flags,
    );
    scans.insert(0, scan);
    notifyListeners(); // provisional card appears immediately (FR-10)

    try {
      scan.result = await api.scoreSms(text, sender);
      scan.offline = false;
    } catch (_) {
      scan.offline = true; // NFR-08: cloud offline, local heuristics stand
    }
    notifyListeners();
    await _persist();
    return scan;
  }

  Future<bool> report(Scan scan, String reportType) async {
    try {
      await api.report(text: scan.text, reportType: reportType);
      scan.reported = true;
      reportsSent += 1;
      notifyListeners();
      await _persist();
      return true;
    } catch (_) {
      return false;
    }
  }

  // ----- Dashboard aggregates (FR-08) -----
  int get totalScans => scans.length;

  Map<String, int> get byClassification {
    final counts = <String, int>{};
    for (final s in scans) {
      final label = s.result?.classification ?? (s.offline ? 'OFFLINE' : 'PENDING');
      counts[label] = (counts[label] ?? 0) + 1;
    }
    return counts;
  }

  int get threatsCaught => scans
      .where((s) =>
          s.result != null &&
          (s.result!.classification == 'HIGH_RISK' ||
              s.result!.classification == 'CRITICAL'))
      .length;
}
