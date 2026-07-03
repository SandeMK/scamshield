/// Platform channel bridge to native Android SMS_RECEIVED broadcasts
/// (Assignment 2 tech stack: Android platform channel).
library;

import 'package:flutter/services.dart';

class IncomingSms {
  final String sender;
  final String body;
  IncomingSms(this.sender, this.body);
}

class SmsChannel {
  static const _events = EventChannel('scamshield/sms');

  static Stream<IncomingSms> stream() => _events
      .receiveBroadcastStream()
      .map((e) => IncomingSms(e['sender'] ?? 'unknown', e['body'] ?? ''));
}
