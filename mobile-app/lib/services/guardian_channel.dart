/// Platform channel bridge to native Android Guardian Alert SMS
/// (Assignment 2 spec FR-09: automatic SMS to a trusted contact on CRITICAL).
library;

import 'package:flutter/services.dart';

class GuardianChannel {
  static const _permission = MethodChannel('scamshield/guardian');
  static const _notify = MethodChannel('scamshield/notify');

  /// Checked before assuming Guardian Alert can fire.
  static Future<bool> hasPermission() async =>
      (await _permission.invokeMethod<bool>('hasSendSmsPermission')) ?? false;

  /// Shows the OS SEND_SMS runtime dialog. Call only after the user has
  /// seen the plain-language explainer and opted in from Settings.
  static Future<bool> requestPermission() async =>
      (await _permission.invokeMethod<bool>('requestSendSmsPermission')) ??
      false;

  /// Fires the automatic Guardian Alert SMS. Handled on the foreground
  /// service, not the activity, so it still works if the app was swiped away.
  static Future<bool> send(String number, String message) async =>
      (await _notify.invokeMethod<bool>('guardianAlert', {
        'number': number,
        'message': message,
      })) ??
      false;
}
