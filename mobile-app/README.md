# ScamShield Mobile App — Flutter (Deliverables 3.2.1 & 3.2.5)

Flutter (Dart) app per the Assignment 2 tech stack: native Android SMS
access via a platform channel, local heuristic pre-checks, cloud hybrid
scoring, colour-coded Material risk cards, reporting, and the analytics
dashboard. Android-only scope (NFR-06), sideloaded for the pilot demo.

## Requirement coverage
| Req | Where |
|---|---|
| FR-01 SMS listening + extraction | `android/.../SmsProtectionService.kt` (FGS EventChannel) + `lib/services/sms_channel.dart` |
| FR-02 HTTPS transmission | `lib/services/api_client.dart` |
| FR-04 Colour-coded Material cards | `lib/screens/home_screen.dart`, `lib/util.dart` |
| FR-05 Report scam / false positive | detail sheet in `home_screen.dart` |
| FR-08 Analytics dashboard | `lib/screens/dashboard_screen.dart` |
| FR-10 Immediate local heuristic warning | `lib/services/local_rules.dart` + provisional card |
| NFR-08 Offline fallback with notice | `lib/services/scan_store.dart` (`offline` flag) |
| US-02 Explanation codes | detail sheet lists code + detail per entry |

## Run (clone-and-run, no setup needed)
```bash
cd mobile-app
flutter pub get
flutter run -d <device-id>   # flutter devices to list
```

Android scaffolding is fully committed. No `setup.sh` step required.

## Demo tips
- **Simulate tab**: injects realistic SA smishing samples through the exact
  same pipeline as real SMS — demo-safe, no network SMS dependency.
- **Real SMS**: text the device from another number; it will appear in the
  Scans tab automatically (foreground service keeps the channel alive even
  when the app is swiped away).
- **Settings tab**: Base URL defaults to the deployed Render API. Override
  to `http://<mac-lan-ip>:8000` if running the API locally.
- **Battery**: grant "Unrestricted" battery access in Samsung Settings →
  Battery → ScamShield to prevent One UI from killing the foreground service.

## Tests
```bash
# Widget + unit tests (§14.2) — runs on host, no device needed
flutter test test/widget_test.dart

# Integration test (§14.3) — requires connected device
flutter test integration_test/app_test.dart -d <device-id>
```
