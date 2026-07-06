/// ScamShield widget + unit tests (Assignment 2 §14.2).
///
/// Coverage:
///  - util.dart: classificationColor, classificationLabel
///  - services/local_rules.dart: runLocalRules
///  - screens/permission_screen.dart: render + button callback
///  - screens/home_screen.dart: empty state, cards, filter chips, detail sheet,
///    report button disabled state

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:scamshield_app/models.dart';
import 'package:scamshield_app/screens/home_screen.dart';
import 'package:scamshield_app/screens/permission_screen.dart';
import 'package:scamshield_app/services/local_rules.dart';
import 'package:scamshield_app/services/scan_store.dart';
import 'package:scamshield_app/util.dart';

// ── Test helpers ──────────────────────────────────────────────────────────────

Widget _wrap(Widget child) => MaterialApp(
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1B5E20)),
        useMaterial3: true,
      ),
      home: Scaffold(body: child),
    );

Scan _fakeScan(
  String classification, {
  int score = 75,
  bool reported = false,
  String text = 'SARS: Your refund is ready. Claim at sars-refund.xyz now.',
}) =>
    Scan(
      id: UniqueKey().toString(),
      text: text,
      sender: '+27821234567',
      timestamp: DateTime.now(),
      source: 'simulated',
      reported: reported,
      result: ScoreResult(
        riskScore: score,
        classification: classification,
        mlConfidence: 0.88,
        ruleSubScore: 55,
        explanationCodes: [
          ExplanationCode(code: 'URL_001', detail: 'Contains a suspicious link'),
          ExplanationCode(code: 'URG_001', detail: 'Urgent or pressuring language'),
          ExplanationCode(code: 'IMP_001', detail: 'References trusted institution'),
        ],
        modelVersion: '1.0.0-test',
      ),
    );

void _seedStore(List<Scan> scans) {
  ScanStore.instance.scans
    ..clear()
    ..addAll(scans);
  ScanStore.instance.loaded = true;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'permission_explained': true});
    ScanStore.instance.scans.clear();
    ScanStore.instance.reportsSent = 0;
    ScanStore.instance.loaded = false;
  });

  // ── classificationColor ─────────────────────────────────────────────────────

  group('classificationColor', () {
    test('CRITICAL returns dark red', () {
      expect(classificationColor('CRITICAL'), const Color(0xFFC62828));
    });
    test('HIGH_RISK returns deep orange', () {
      expect(classificationColor('HIGH_RISK'), const Color(0xFFE64A19));
    });
    test('MEDIUM_RISK returns amber', () {
      expect(classificationColor('MEDIUM_RISK'), const Color(0xFFF9A825));
    });
    test('LOW_RISK returns olive', () {
      expect(classificationColor('LOW_RISK'), const Color(0xFF9E9D24));
    });
    test('SAFE returns green', () {
      expect(classificationColor('SAFE'), const Color(0xFF2E7D32));
    });
    test('unknown label returns grey', () {
      expect(classificationColor('PENDING'), const Color(0xFF757575));
    });
  });

  // ── classificationLabel ─────────────────────────────────────────────────────

  group('classificationLabel', () {
    test('replaces underscores with spaces', () {
      expect(classificationLabel('HIGH_RISK'), 'HIGH RISK');
      expect(classificationLabel('MEDIUM_RISK'), 'MEDIUM RISK');
    });
    test('no underscores left unchanged', () {
      expect(classificationLabel('SAFE'), 'SAFE');
      expect(classificationLabel('CRITICAL'), 'CRITICAL');
    });
  });

  // ── runLocalRules ───────────────────────────────────────────────────────────

  group('runLocalRules', () {
    test('clean message scores 0 with no flags', () {
      final r = runLocalRules('Hey, are we still on for lunch tomorrow?');
      expect(r.score, 0);
      expect(r.flags, isEmpty);
      expect(r.highRisk, isFalse);
    });

    test('URL detection adds 10 points', () {
      final r = runLocalRules('Visit http://example.com for details');
      expect(r.score, greaterThanOrEqualTo(10));
      expect(r.flags, contains('Contains a link'));
    });

    test('URL shortener adds 20 points', () {
      final r = runLocalRules('Click here: bit.ly/abc123');
      expect(r.score, greaterThanOrEqualTo(20));
      expect(r.flags, contains('Shortened link hides destination'));
    });

    test('IP-based URL adds 25 points', () {
      final r = runLocalRules('Go to http://196.23.155.8/track now');
      expect(r.score, greaterThanOrEqualTo(25));
      expect(r.flags, contains('Link uses a raw IP address'));
    });

    test('urgency language adds 15 points', () {
      final r = runLocalRules('Your account has been suspended immediately');
      expect(r.score, greaterThanOrEqualTo(15));
      expect(r.flags, contains('Urgent or pressuring language'));
    });

    test('SA institution impersonation adds 15 points', () {
      final r = runLocalRules('SARS needs you to reconfirm your details');
      expect(r.score, greaterThanOrEqualTo(15));
      expect(r.flags, contains('References trusted institution'));
    });

    test('credential request adds 20 points', () {
      final r = runLocalRules('Please confirm your PIN to proceed');
      expect(r.score, greaterThanOrEqualTo(20));
      expect(r.flags, contains('Asks for credentials or PIN'));
    });

    test('combined signals mark message as high risk', () {
      final r = runLocalRules(
          'URGENT: SARS refund held. Verify your PIN at http://bit.ly/sars now');
      expect(r.highRisk, isTrue);
      expect(r.score, greaterThanOrEqualTo(50));
    });

    test('score never exceeds 100', () {
      final r = runLocalRules(
          'URGENT account suspended! OTP PIN verify SARS bank '
          'bit.ly/x http://1.2.3.4/x won prize congratulations');
      expect(r.score, lessThanOrEqualTo(100));
    });
  });

  // ── PermissionScreen ────────────────────────────────────────────────────────

  group('PermissionScreen', () {
    testWidgets('renders title and enable button', (tester) async {
      await tester.pumpWidget(_wrap(PermissionScreen(onDone: () {})));
      await tester.pumpAndSettle();

      expect(find.text('ScamShield protects you'), findsOneWidget);
      expect(find.text('Enable protection'), findsOneWidget);
    });

    testWidgets('renders all three privacy bullet points', (tester) async {
      await tester.pumpWidget(_wrap(PermissionScreen(onDone: () {})));
      await tester.pumpAndSettle();

      expect(find.textContaining('SHA-256'), findsOneWidget);
      expect(find.textContaining('scored on your device'), findsOneWidget);
      expect(find.textContaining('No message content'), findsOneWidget);
    });

    testWidgets('calls onDone callback when button tapped', (tester) async {
      bool called = false;
      await tester.pumpWidget(_wrap(PermissionScreen(onDone: () => called = true)));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Enable protection'));
      await tester.pumpAndSettle();

      expect(called, isTrue);
    });
  });

  // ── HomeScreen — empty state ─────────────────────────────────────────────────

  group('HomeScreen empty state', () {
    testWidgets('shows empty state title when no scans', (tester) async {
      _seedStore([]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.text('No messages scanned yet'), findsOneWidget);
    });

    testWidgets('shows shield icon in empty state', (tester) async {
      _seedStore([]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });

    testWidgets('Suspicious+ empty state has different copy', (tester) async {
      _seedStore([]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Suspicious+'));
      await tester.pumpAndSettle();

      expect(find.text('No suspicious messages'), findsOneWidget);
    });
  });

  // ── HomeScreen — card rendering ──────────────────────────────────────────────

  group('HomeScreen scan cards', () {
    testWidgets('CRITICAL scan card shows CRITICAL label', (tester) async {
      _seedStore([_fakeScan('CRITICAL', score: 95)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.textContaining('CRITICAL'), findsWidgets);
    });

    testWidgets('SAFE scan card shows SAFE label', (tester) async {
      _seedStore([_fakeScan('SAFE', score: 5)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.textContaining('SAFE'), findsWidgets);
    });

    testWidgets('multiple scans all render as cards', (tester) async {
      _seedStore([
        _fakeScan('CRITICAL', score: 95),
        _fakeScan('HIGH_RISK', score: 80),
        _fakeScan('SAFE', score: 5),
      ]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.byType(Card), findsNWidgets(3));
    });
  });

  // ── HomeScreen — filter chips ─────────────────────────────────────────────────

  group('HomeScreen filter chips', () {
    testWidgets('All / Suspicious+ / Reported chips are present', (tester) async {
      _seedStore([]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Suspicious+'), findsOneWidget);
      expect(find.text('Reported'), findsOneWidget);
    });

    testWidgets('Suspicious+ filter hides SAFE card', (tester) async {
      _seedStore([
        _fakeScan('CRITICAL', score: 95, text: 'Scam message here'),
        _fakeScan('SAFE', score: 5, text: 'Hey are you free for lunch?'),
      ]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Suspicious+'));
      await tester.pumpAndSettle();

      // Only CRITICAL card remains
      expect(find.byType(Card), findsOneWidget);
      expect(find.text('Scam message here'), findsOneWidget);
      expect(find.text('Hey are you free for lunch?'), findsNothing);
    });

    testWidgets('Reported filter shows only reported scans', (tester) async {
      _seedStore([
        _fakeScan('CRITICAL', score: 95, reported: true, text: 'Reported scam'),
        _fakeScan('HIGH_RISK', score: 80, reported: false, text: 'Unreported scam'),
      ]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Reported'));
      await tester.pumpAndSettle();

      expect(find.byType(Card), findsOneWidget);
      expect(find.text('Reported scam'), findsOneWidget);
      expect(find.text('Unreported scam'), findsNothing);
    });

    testWidgets('All filter restores all cards', (tester) async {
      _seedStore([
        _fakeScan('CRITICAL', score: 95),
        _fakeScan('SAFE', score: 5),
      ]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Suspicious+'));
      await tester.pumpAndSettle();
      expect(find.byType(Card), findsOneWidget);

      await tester.tap(find.text('All'));
      await tester.pumpAndSettle();
      expect(find.byType(Card), findsNWidgets(2));
    });
  });

  // ── HomeScreen — detail sheet ─────────────────────────────────────────────────

  group('HomeScreen detail sheet', () {
    testWidgets('tapping card opens sheet with explanation codes', (tester) async {
      _seedStore([_fakeScan('HIGH_RISK', score: 80)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ListTile).first);
      await tester.pumpAndSettle();

      expect(find.text('Why this was flagged'), findsOneWidget);
      expect(find.text('Contains a suspicious link'), findsOneWidget);
      expect(find.text('Urgent or pressuring language'), findsOneWidget);
      expect(find.text('References trusted institution'), findsOneWidget);
    });

    testWidgets('detail sheet shows explanation code identifiers', (tester) async {
      _seedStore([_fakeScan('CRITICAL', score: 95)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ListTile).first);
      await tester.pumpAndSettle();

      expect(find.text('URL_001'), findsOneWidget);
      expect(find.text('URG_001'), findsOneWidget);
      expect(find.text('IMP_001'), findsOneWidget);
    });

    testWidgets('detail sheet shows model version after scrolling', (tester) async {
      _seedStore([_fakeScan('CRITICAL', score: 95)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ListTile).first);
      await tester.pumpAndSettle();

      // Scroll sheet down to reveal model version below explanation codes
      await tester.drag(find.byType(ListView).last, const Offset(0, -300));
      await tester.pumpAndSettle();

      expect(find.textContaining('1.0.0-test'), findsOneWidget);
    });

    testWidgets('report button disabled for already-reported scan', (tester) async {
      _seedStore([_fakeScan('CRITICAL', score: 95, reported: true)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ListTile).first);
      await tester.pumpAndSettle();

      await tester.drag(find.byType(ListView).last, const Offset(0, -300));
      await tester.pumpAndSettle();

      // disabled button has null onPressed
      final reportBtns = tester.widgetList<FilledButton>(find.byType(FilledButton));
      expect(reportBtns.any((b) => b.onPressed == null), isTrue);
    });

    testWidgets('report button enabled for unreported scan', (tester) async {
      _seedStore([_fakeScan('HIGH_RISK', score: 80, reported: false)]);
      await tester.pumpWidget(_wrap(const HomeScreen()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ListTile).first);
      await tester.pumpAndSettle();

      await tester.drag(find.byType(ListView).last, const Offset(0, -300));
      await tester.pumpAndSettle();

      final reportBtns = tester.widgetList<FilledButton>(find.byType(FilledButton));
      expect(reportBtns.any((b) => b.onPressed != null), isTrue);
    });
  });
}
