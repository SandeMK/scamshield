/// Anonymised device identifier — generated once at first launch and
/// persisted locally. Exists whether or not a profile is ever created
/// (Assignment 2 §5.1: device_id is a hub, not a chain).
library;

import 'dart:math';
import 'package:shared_preferences/shared_preferences.dart';

class DeviceId {
  static String? _cached;

  static Future<String> get() async {
    if (_cached != null) return _cached!;
    final prefs = await SharedPreferences.getInstance();
    var id = prefs.getString('deviceId');
    if (id == null) {
      id = _generate();
      await prefs.setString('deviceId', id);
    }
    _cached = id;
    return id;
  }

  static String _generate() {
    final rand = Random.secure();
    final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
