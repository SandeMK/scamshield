/// Anonymised device identifier (Assignment 2 §5.1: device_id is a hub, not
/// a chain). Exists whether or not a profile is ever created.
///
/// On Android it is derived natively from ANDROID_ID (SHA-256, first 32 hex
/// chars — see ScamShieldApp.stableDeviceId), so it survives an uninstall /
/// reinstall on the same phone and the profile reappears without recovery.
/// Recovery (FR-16) is still needed on a new phone or after a factory reset.
/// Elsewhere (tests, or if the platform call fails) it falls back to the
/// stored value, or a fresh random id generated once and persisted.
library;

import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DeviceId {
  static const _channel = MethodChannel('scamshield/device');
  static final _idShape = RegExp(r'^[0-9a-f]{32}$');
  static String? _cached;

  static Future<String> get() async {
    if (_cached != null) return _cached!;
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString('deviceId');
    // The derived id wins over a stored one, so an install that still holds
    // an older random id moves onto the stable id (its profile is then
    // re-linked once via recovery).
    final id = await _stableId() ?? stored ?? _generate();
    if (id != stored) await prefs.setString('deviceId', id);
    _cached = id;
    return id;
  }

  static Future<String?> _stableId() async {
    try {
      final id = await _channel.invokeMethod<String>('getStableId');
      return id != null && _idShape.hasMatch(id) ? id : null;
    } catch (_) {
      return null; // no Android host (tests) or no ANDROID_ID
    }
  }

  static String _generate() {
    final rand = Random.secure();
    final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }

  @visibleForTesting
  static void resetCache() => _cached = null;
}
