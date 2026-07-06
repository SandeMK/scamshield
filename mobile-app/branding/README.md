# ScamShield Branding

`icon.svg` is the master (edit this, re-render PNGs with cairosvg).
Rendered: `icon-1024.png`, `icon-512.png`, `icon-foreground.png`
(adaptive foreground: transparent, artwork in the 66% safe zone).
Brand colours: primary #1B5E20, gradient top #2E7D32, alert #E64A19.

## Wiring the launcher icon (flutter_launcher_icons)
In `mobile-app/app/pubspec.yaml`:
```yaml
dev_dependencies:
  flutter_launcher_icons: ^0.14.1

flutter_launcher_icons:
  android: true
  image_path: "../branding/icon-1024.png"
  adaptive_icon_background: "#1B5E20"
  adaptive_icon_foreground: "../branding/icon-foreground.png"
```
Then: `cd mobile-app/app && dart run flutter_launcher_icons`

## App display name
Set `android:label="ScamShield"` on the `<application>` tag in
`mobile-app/app/android/app/src/main/AndroidManifest.xml`
(flutter create defaults it to "scamshield_app").
Ideally patch this in `setup.sh` alongside the permissions patch so
regenerating the project keeps the name.
