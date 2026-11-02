/// Platform channel bridge for tapped scam-alert notifications: the app
/// opens on the Scans tab with that scan's detail sheet.
library;

import 'package:flutter/services.dart';

class AlertTapChannel {
  static const _channel = MethodChannel('scamshield/alert_tap');

  /// Pulls and clears the scan id of a tapped alert — used at startup (cold
  /// start) and after an 'onAlertTap' signal (warm start). Null when no
  /// alert was tapped; empty when the alert carried no scan id.
  static Future<String?> pullScanId() =>
      _channel.invokeMethod<String>('getPendingScanId');

  /// Registers a callback fired when an alert is tapped while the app is
  /// already running. The callback should re-pull via [pullScanId].
  static void listenForSignal(void Function() onTap) {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onAlertTap') onTap();
      return null;
    });
  }
}
