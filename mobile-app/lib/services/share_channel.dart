/// Platform channel bridge to native Android share-sheet intents
/// (Assignment 2 spec FR-10: Share-to-ScamShield).
library;

import 'package:flutter/services.dart';

class ShareChannel {
  static const _channel = MethodChannel('scamshield/share');

  /// Pulls and clears any pending shared text held natively — used both
  /// at startup (cold start) and after an 'onShare' signal (warm start).
  static Future<String?> pullText() =>
      _channel.invokeMethod<String>('getInitialText');

  /// Registers a callback fired when a share arrives while the app is
  /// already running. The callback should re-pull via [pullText].
  static void listenForSignal(void Function() onShare) {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onShare') onShare();
      return null;
    });
  }
}
