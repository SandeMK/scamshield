/// ScamShield integration test (Assignment 2 §14.3).
///
/// Tests the full end-to-end flow:
///   Simulator tab → type message → Analyze → result appears on Scans tab.
///
/// Run on device: flutter test integration_test/app_test.dart -d <device-id>

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:scamshield_app/main.dart';
import 'package:scamshield_app/services/scan_store.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    // Skip permission screen; start with empty scan history.
    SharedPreferences.setMockInitialValues({'permission_explained': true});
    ScanStore.instance.scans.clear();
    ScanStore.instance.loaded = false;
    ScanStore.instance.reportsSent = 0;
  });

  testWidgets(
    'Simulate tab: typing and analyzing a message shows a scan card on the Scans tab',
    (tester) async {
      await tester.pumpWidget(const ScamShieldApp(firstLaunch: false));
      await tester.pumpAndSettle();

      // ── Navigate to Simulate tab ─────────────────────────────────────────────
      await tester.tap(find.byIcon(Icons.science_outlined));
      await tester.pumpAndSettle();

      expect(find.text('Simulate an incoming SMS'), findsOneWidget);

      // ── Type a scam message ──────────────────────────────────────────────────
      const message =
          'URGENT: Your SARS refund of R3,450 is ready. '
          'Verify your ID at http://sars-efiling-refund.xyz within 24 hours.';

      await tester.enterText(find.byType(TextField).first, message);
      await tester.pumpAndSettle();

      // ── Tap Analyze ──────────────────────────────────────────────────────────
      await tester.tap(find.text('Analyze'));

      // Pump one frame to allow ScanStore.process() to insert the provisional
      // scan (local heuristics fire synchronously before the async API call).
      await tester.pump(const Duration(milliseconds: 200));

      // ── Navigate to Scans tab ────────────────────────────────────────────────
      await tester.tap(find.byIcon(Icons.shield_outlined));
      await tester.pumpAndSettle();

      // ── Verify scan card appeared ────────────────────────────────────────────
      expect(
        find.textContaining('URGENT: Your SARS refund'),
        findsOneWidget,
        reason: 'Scan card should appear immediately after local heuristics run',
      );

      // Scans tab should no longer show the empty state.
      expect(find.text('No messages scanned yet'), findsNothing);
    },
  );

  testWidgets(
    'Simulate tab: sample message tap runs through pipeline',
    (tester) async {
      await tester.pumpWidget(const ScamShieldApp(firstLaunch: false));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.science_outlined));
      await tester.pumpAndSettle();

      // Tap the first sample (SARS impersonation)
      await tester.tap(find.byIcon(Icons.play_arrow).first);
      await tester.pump(const Duration(milliseconds: 200));

      // Navigate to Scans tab and verify card exists
      await tester.tap(find.byIcon(Icons.shield_outlined));
      await tester.pumpAndSettle();

      expect(find.byType(Card), findsAtLeastNWidgets(1));
      expect(find.text('No messages scanned yet'), findsNothing);
    },
  );

  testWidgets(
    'Permission screen: first launch shows explainer, Enable routes to Scans tab',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      await tester.pumpWidget(const ScamShieldApp(firstLaunch: true));
      await tester.pumpAndSettle();

      expect(find.text('ScamShield protects you'), findsOneWidget);
      expect(find.text('Enable protection'), findsOneWidget);

      await tester.tap(find.text('Enable protection'));
      await tester.pumpAndSettle();

      // After enabling, should be on the main scaffold (Scans tab)
      expect(find.byIcon(Icons.shield_outlined), findsWidgets);
      expect(find.text('ScamShield protects you'), findsNothing);
    },
  );
}
