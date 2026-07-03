#!/usr/bin/env bash
# One-time setup: generates the Flutter build scaffolding for YOUR installed
# Flutter version, then drops the ScamShield source in. Run from android/.
set -e

if ! command -v flutter &> /dev/null; then
    echo "Flutter SDK not found. Install it first: https://docs.flutter.dev/get-started/install"
    exit 1
fi

echo "==> Creating Flutter project scaffolding..."
flutter create --org com.scamshield --project-name scamshield_app --platforms android app

echo "==> Installing ScamShield source..."
cp -r lib app/
cp pubspec.yaml app/pubspec.yaml

MAIN_ACTIVITY=$(find app/android -name MainActivity.kt)
cp platform/MainActivity.kt "$MAIN_ACTIVITY"

MANIFEST=app/android/app/src/main/AndroidManifest.xml
# Add SMS + internet permissions above the <application> tag
python3 - << 'PYEOF'
manifest = "app/android/app/src/main/AndroidManifest.xml"
s = open(manifest).read()
perms = ('    <uses-permission android:name="android.permission.INTERNET" />\n'
         '    <uses-permission android:name="android.permission.RECEIVE_SMS" />\n')
if "RECEIVE_SMS" not in s:
    s = s.replace("<application", perms + "    <application", 1)
open(manifest, "w").write(s)
print("manifest patched")
PYEOF

cd app && flutter pub get
echo ""
echo "==> Done. Run the app with an emulator or device connected:"
echo "    cd app && flutter run"
