#!/usr/bin/env bash
# One-time setup: generates the Flutter build scaffolding for YOUR installed
# Flutter version, then drops the ScamShield source in. Run from mobile-app/.
set -e

if ! command -v flutter &> /dev/null; then
    echo "Flutter SDK not found. Install it first: https://docs.flutter.dev/get-started/install"
    exit 1
fi

echo "==> Creating Flutter project scaffolding..."
flutter create --org com.scamshield --project-name scamshield_app --platforms android .

echo "==> Installing MainActivity..."
MAIN_ACTIVITY=$(find android -name MainActivity.kt)
cp platform/MainActivity.kt "$MAIN_ACTIVITY"

python3 - << 'PYEOF'
manifest = "android/app/src/main/AndroidManifest.xml"
s = open(manifest).read()
perms = ('    <uses-permission android:name="android.permission.INTERNET" />\n'
         '    <uses-permission android:name="android.permission.RECEIVE_SMS" />\n')
if "RECEIVE_SMS" not in s:
    s = s.replace("<application", perms + "    <application", 1)
open(manifest, "w").write(s)
print("manifest patched")
PYEOF

flutter pub get
echo ""
echo "==> Done. Run the app with a device connected:"
echo "    flutter run"
