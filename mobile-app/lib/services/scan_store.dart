/// Central scan pipeline + persistent store.
///
/// Every message (real SMS or simulated) flows through [process]:
///   1. FR-10 local heuristics -> instant provisional result
///   2. Cloud hybrid scoring -> final result
///   3. NFR-08 offline fallback: keep local result, mark cloud offline
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models.dart';
import 'api_client.dart';
import 'device_id.dart';
import 'guardian_channel.dart';
import 'local_rules.dart';

const _notifyChannel = MethodChannel('scamshield/notify');

const guardianAlertPrefix = 'ScamShield Guardian Alert:';

/// Classification labels in rising order of risk (FR-15 alert threshold).
const riskLevels = ['SAFE', 'LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK', 'CRITICAL'];

/// Threshold used when the device has no profile: alert on HIGH_RISK and
/// CRITICAL only, the behaviour before FR-15 was enforced.
const defaultAlertThreshold = 'HIGH_RISK';

/// shared_preferences key holding a local copy of the profile's
/// alert_threshold. Settings writes it whenever the profile is loaded or the
/// preference saved, so alerts follow it offline and with the app swiped away.
const alertThresholdKey = 'alertThreshold';

/// FR-15: true when [classification] is at or above [threshold]. A missing
/// classification (offline scan) never alerts; an unknown threshold falls
/// back to [defaultAlertThreshold].
bool meetsAlertThreshold(String? classification, String? threshold) {
  final c = riskLevels.indexOf(classification ?? '');
  if (c < 0) return false;
  var t = riskLevels.indexOf(threshold ?? '');
  if (t < 0) t = riskLevels.indexOf(defaultAlertThreshold);
  return c >= t;
}

/// FR-09 Guardian Alert SMS body for [text], or null when [text] is itself a
/// Guardian Alert. The alert quotes the scam, so it scores CRITICAL too; if
/// the trusted contact also runs ScamShield (or is the other SIM on the same
/// phone) it would otherwise text back and forth forever. The preview is cut
/// with ASCII '...' (not '…') so the SMS stays GSM-7 — a Unicode body sends
/// SmsManager.divideMessage() down a path that needs READ_PHONE_STATE on
/// some devices (Samsung S938B, Android 16).
String? guardianAlertMessage(String text) {
  if (text.trimLeft().startsWith(guardianAlertPrefix)) return null;
  final preview = text.length > 80 ? '${text.substring(0, 80)}...' : text;
  return '$guardianAlertPrefix a message received on a '
      'phone you are the trusted contact for was just classified CRITICAL '
      '(likely scam). They may need help. Message: "$preview"';
}

// ── FR-15 retroactive re-classification ─────────────────────────────────────
// The server keeps no scans, so only the phone knows which messages carried
// a link that the shared threat DB has learned about since (daily feeds,
// other users' reports). It re-scores recent link-bearing scans through the
// same /score/sms endpoint, keeping scoring in one place.

/// shared_preferences key: local copy of the profile's retroactive_updates
/// (absent = on, the server default).
const retroactiveUpdatesKey = 'retroactiveUpdates';
const _lastRecheckKey = 'lastRecheckAt';
const recheckWindow = Duration(days: 14);
const recheckMaxPerRun = 25;
const recheckMinInterval = Duration(hours: 1);
const recheckPeriod = Duration(hours: 6);

bool _hasIntelMatch(ScoreResult? r) =>
    r?.explanationCodes.any((c) => c.code == 'INTEL_MATCH') ?? false;

/// Scans worth re-checking, newest first: cloud-scored, carrying a link, from
/// the last [recheckWindow], below CRITICAL with no intel match yet, and not
/// reported by this user (their own scam report adds the link to the DB and
/// must not come back as a "re-classified" alert).
List<Scan> recheckCandidates(List<Scan> scans, DateTime now) => scans
    .where((s) =>
        s.result != null &&
        !s.reported &&
        s.result!.classification != 'CRITICAL' &&
        !_hasIntelMatch(s.result) &&
        now.difference(s.timestamp) <= recheckWindow &&
        hasLink(s.text))
    .take(recheckMaxPerRun)
    .toList();

/// A re-check result replaces the stored one only when it gained an
/// INTEL_MATCH and raised the risk level — so a model update alone never
/// re-classifies, and an earlier warning is never lowered.
bool isRetroactiveUpgrade(ScoreResult old, ScoreResult fresh) =>
    !_hasIntelMatch(old) &&
    _hasIntelMatch(fresh) &&
    riskLevels.indexOf(fresh.classification) >
        riskLevels.indexOf(old.classification);

String _alertLabel(String? c) => switch (c) {
      'CRITICAL' => 'CRITICAL scam',
      'HIGH_RISK' => 'High-risk message',
      'MEDIUM_RISK' => 'Suspicious message',
      'LOW_RISK' => 'Low-risk message',
      _ => 'Safe message',
    };

String _preview(String text) =>
    text.length > 60 ? '${text.substring(0, 60)}…' : text;

class ScanStore extends ChangeNotifier {
  ScanStore._();
  static final instance = ScanStore._();

  final api = ApiClient();
  final List<Scan> scans = [];
  int reportsSent = 0;
  bool loaded = false;
  Future<void>? _loading;

  /// Loads persisted scans once; concurrent callers (startup and a tapped
  /// alert) share one in-flight load. Setting [loaded] false allows a reload.
  Future<void> load() {
    if (loaded) return Future.value();
    return _loading ??= _load().whenComplete(() => _loading = null);
  }

  Future<void> _load() async {
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
    _maybePostAlert(scan); // FR-15: follows the saved alert threshold
    _maybeGuardianAlert(scan); // FR-09: fires only on the returned cloud result
    return scan;
  }

  /// Posts a phone notification when the cloud classification meets the
  /// user's alert threshold (FR-15). Offline scans never alert.
  Future<void> _maybePostAlert(Scan scan) async {
    final c = scan.result?.classification;
    final prefs = await SharedPreferences.getInstance();
    if (!meetsAlertThreshold(c, prefs.getString(alertThresholdKey))) return;
    _notifyChannel.invokeMethod('alert', {
      'title': '${_alertLabel(c)} from ${scan.sender}',
      'body': _preview(scan.text),
      'scanId': scan.id, // tapping the alert opens this scan's detail sheet
    }).catchError((_) {}); // non-fatal if service not running
  }

  // ----- FR-15 retroactive re-classification -----

  bool _rechecking = false;
  Timer? _recheckTimer;

  /// Re-checks every [recheckPeriod] while the process lives (the foreground
  /// service keeps it alive). Idempotent.
  void startRecheckTimer() {
    _recheckTimer ??= Timer.periodic(recheckPeriod, (_) => maybeRecheck());
  }

  /// Throttled re-check for app open/resume and the timer: at most once per
  /// [recheckMinInterval]. Returns the number of scans re-classified.
  Future<int> maybeRecheck() async {
    final prefs = await SharedPreferences.getInstance();
    final last = prefs.getInt(_lastRecheckKey);
    if (last != null &&
        DateTime.now().difference(DateTime.fromMillisecondsSinceEpoch(last)) <
            recheckMinInterval) {
      return 0;
    }
    return recheckRecent();
  }

  /// Re-scores [recheckCandidates] one at a time, stopping at the first
  /// network failure. Re-checks run whether or not alerts are enabled, so
  /// stored results stay current; only the alert follows the preference.
  /// No Guardian SMS: the message may be days old (FR-09 covers the first
  /// result only).
  Future<int> recheckRecent() async {
    if (_rechecking) return 0;
    _rechecking = true;
    var upgraded = 0;
    try {
      await load();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_lastRecheckKey, DateTime.now().millisecondsSinceEpoch);
      for (final scan in recheckCandidates(scans, DateTime.now())) {
        final ScoreResult fresh;
        try {
          fresh = await api.scoreSms(scan.text, scan.sender);
        } catch (_) {
          break; // offline or API down: try again next time
        }
        final old = scan.result!;
        if (!isRetroactiveUpgrade(old, fresh)) continue;
        scan
          ..previousClassification = old.classification
          ..reclassifiedAt = DateTime.now()
          ..result = fresh;
        upgraded++;
        await _maybePostRetroactiveAlert(scan, prefs);
      }
      if (upgraded > 0) {
        notifyListeners();
        await _persist();
      }
    } finally {
      _rechecking = false;
    }
    return upgraded;
  }

  Future<void> _maybePostRetroactiveAlert(
      Scan scan, SharedPreferences prefs) async {
    if (prefs.getBool(retroactiveUpdatesKey) == false) return;
    final c = scan.result?.classification;
    if (!meetsAlertThreshold(c, prefs.getString(alertThresholdKey))) return;
    try {
      await _notifyChannel.invokeMethod('alert', {
        'title': 'Earlier message from ${scan.sender} is now: ${_alertLabel(c)}',
        'body': 'Its link was since found in the threat database. '
            '"${_preview(scan.text)}"',
        'scanId': scan.id,
      });
    } catch (_) {} // non-fatal if service not running
  }

  /// FR-09 Guardian Alert. Gated on scan.result, which is only ever set from
  /// the cloud response — never on localScore — so an unreachable API (NFR-02
  /// offline path) never fires this, matching the activity/sequence diagrams
  /// where the branch sits after the final colour-coded result.
  Future<void> _maybeGuardianAlert(Scan scan) async {
    if (scan.result?.classification != 'CRITICAL') return;
    final message = guardianAlertMessage(scan.text);
    if (message == null) return;
    final prefs = await SharedPreferences.getInstance();
    final contact = prefs.getString('guardianContact');
    if (contact == null || contact.isEmpty) return;
    try {
      await GuardianChannel.send(contact, message);
    } catch (_) {} // never let a channel/permission failure break scoring
  }

  Future<bool> report(Scan scan, String reportType) async {
    try {
      final deviceId = await DeviceId.get();
      await api.report(
          text: scan.text, reportType: reportType, deviceId: deviceId);
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
