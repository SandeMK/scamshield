# ScamShield Mobile App — Flutter (Deliverables 3.2.1 & 3.2.5)

Flutter (Dart) app per the Assignment 2 tech stack: native Android SMS
access via a platform channel, local heuristic pre-checks, cloud hybrid
scoring, colour-coded Material risk cards, reporting, and the analytics
dashboard. Android-only scope (NFR-06), sideloaded for the pilot demo.

## Requirement coverage
| Req | Where |
|---|---|
| FR-01 SMS listening + extraction | `platform/MainActivity.kt` (EventChannel) + `lib/main.dart` |
| FR-02 HTTPS transmission | `lib/services/api_client.dart` |
| FR-04 Colour-coded Material cards | `lib/screens/home_screen.dart`, `lib/util.dart` |
| FR-05 Report scam / false positive | detail sheet in `home_screen.dart` |
| FR-08 Analytics dashboard | `lib/screens/dashboard_screen.dart` |
| FR-10 Immediate local heuristic warning | `lib/services/local_rules.dart` + provisional card |
| NFR-08 Offline fallback with notice | `lib/services/scan_store.dart` (`offline` flag) |
| US-02 Explanation codes | detail sheet lists code + detail per entry |

## Setup (one time, on your machine)
```bash
cd mobile-app
./setup.sh        # runs flutter create, installs source, patches manifest
cd app
flutter run       # with an emulator running or device connected
```

## Demo tips
- **Simulate tab**: injects realistic SA smishing samples through the exact
  same pipeline as real SMS — demo-safe, no network SMS dependency.
- **Real SMS on the emulator**: with the app open, use Android Studio's
  Extended Controls (⋯ on the emulator toolbar) -> Phone -> SMS to send a
  message; it will appear in the Scans tab automatically.
- **Settings tab**: point Base URL at `http://10.0.2.2:8000` while running
  the API locally (`cd api && uvicorn main:app`), or at the deployed URL.
- Note: SMS capture works while the app is running (foreground/background
  with the activity alive). Persistent background capture is intentionally
  out of pilot scope.
