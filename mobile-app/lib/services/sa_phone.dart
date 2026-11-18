/// South African mobile number validation for the FR-09 Guardian Alert
/// trusted contact. Guardian sends an SMS, so only mobile ranges qualify:
/// landlines (01x-05x) can't receive one, and 080 (toll-free), 086
/// (sharecall) and 087 (VoIP) are not mobile numbers.
library;

final _separators = RegExp(r'[\s\-().]');
final _saMobile = RegExp(r'^(?:\+27|0027|27|0)([6-8]\d{8})$');
final _nonMobile = RegExp(r'^8[067]');

/// The number in E.164 form (+27XXXXXXXXX), or null if [input] is not a
/// South African mobile number. Accepts the usual ways of writing one:
/// 082 123 4567, 082-123-4567, (082) 123 4567, +27 82 123 4567,
/// 27821234567, 0027821234567.
String? normalizeSaMobile(String input) {
  final match = _saMobile.firstMatch(input.replaceAll(_separators, ''));
  if (match == null) return null;
  final national = match.group(1)!;
  if (_nonMobile.hasMatch(national)) return null;
  return '+27$national';
}

/// Local display form (082 123 4567) of a South African mobile number;
/// anything that isn't one is returned unchanged.
String formatSaMobile(String input) {
  final e164 = normalizeSaMobile(input);
  if (e164 == null) return input;
  final n = '0${e164.substring(3)}';
  return '${n.substring(0, 3)} ${n.substring(3, 6)} ${n.substring(6)}';
}
