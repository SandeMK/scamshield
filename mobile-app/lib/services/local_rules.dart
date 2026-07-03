/// FR-10: lightweight local heuristic checks for an immediate warning
/// before the cloud response arrives. Dart port of ml/features.py rules.
library;

final _urlRe = RegExp(
    r'(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(com|net|org|co\.za|info|xyz|top|click|link|site|online)\b\S*)',
    caseSensitive: false);
final _shortenerRe = RegExp(
    r'\b(bit\.ly|tinyurl\.com|goo\.gl|t\.co|is\.gd|ow\.ly|cutt\.ly|rb\.gy)\b',
    caseSensitive: false);
final _ipUrlRe = RegExp(r'https?://\d{1,3}(\.\d{1,3}){3}');

const _urgency = ['urgent', 'immediately', 'expires', 'final notice',
  'last chance', 'suspended', 'deactivated', 'verify now', 'act fast'];
const _impersonation = ['sars', 'fnb', 'absa', 'nedbank', 'capitec',
  'standard bank', 'tymebank', 'sassa', 'nsfas', 'post office', 'courier',
  'efiling', 'vodacom', 'mtn', 'telkom', 'bank', 'account'];
const _prize = ['won', 'winner', 'prize', 'claim', 'reward',
  'congratulations', 'free', 'voucher', 'lottery', 'selected'];
const _credentials = ['password', 'pin', 'otp', 'one-time', 'login',
  'verify', 'confirm', 'id number', 'card number', 'cvv'];

class LocalRuleResult {
  final int score; // 0-100
  final List<String> flags;
  LocalRuleResult(this.score, this.flags);
  bool get highRisk => score >= 50;
}

LocalRuleResult runLocalRules(String text) {
  final t = text.toLowerCase();
  var score = 0;
  final flags = <String>[];

  void check(bool hit, int weight, String flag) {
    if (hit) {
      score += weight;
      flags.add(flag);
    }
  }

  check(_urlRe.hasMatch(text), 10, 'Contains a link');
  check(_shortenerRe.hasMatch(text), 20, 'Shortened link hides destination');
  check(_ipUrlRe.hasMatch(text), 25, 'Link uses a raw IP address');
  check(_urgency.any(t.contains), 15, 'Urgent or pressuring language');
  check(_impersonation.any(t.contains), 15, 'References trusted institution');
  check(_prize.any(t.contains), 15, 'Promises a prize or reward');
  check(_credentials.any(t.contains), 20, 'Asks for credentials or PIN');

  return LocalRuleResult(score.clamp(0, 100), flags);
}
