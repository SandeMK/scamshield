/// FR-10: lightweight local heuristic checks for an immediate warning
/// before the cloud response arrives. Dart port of ml/features.py rules.
library;

// Port of LINK_PATTERN in ml/features.py (A4): http(s)/www links,
// shorteners, bare host.tld/path with any TLD, and bare host.tld for
// familiar TLDs only. Email addresses (preceded by '@') don't count.
const _urlShorteners = ['bit.ly', 't.co', 'is.gd', 'rb.gy', 'cutt.ly',
  'tinyurl.com', 'ow.ly', 'shorturl.at', 'tiny.cc', 'goo.gl'];
const _bareLinkTlds = ['com', 'net', 'org', 'info', 'biz', 'xyz', 'top',
  'click', 'link', 'site', 'online', 'live', 'shop', 'app', 'io', 'za'];
const _linkHost = r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+';
const _linkChar = r'''[^\s<>"']''';
const _linkHostEnd = r'(?![\w-]|\.[a-z0-9])';
final _linkRe = RegExp(
    [
      r'(?<![@\w.-])(?:',
      'https?://$_linkChar+',
      '|www\\.$_linkChar+',
      '|(?:${_urlShorteners.map(RegExp.escape).join('|')})$_linkHostEnd'
          '(?:/$_linkChar*)?',
      '|$_linkHost[a-z]{2,24}/$_linkChar*',
      '|$_linkHost(?:${_bareLinkTlds.join('|')})$_linkHostEnd',
      ')',
    ].join(),
    caseSensitive: false);
final _shortenerRe = RegExp(
    '\\b(${_urlShorteners.map(RegExp.escape).join('|')})\\b',
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

// Port of BRANDS in ml/features.py — keep in sync (ml/tests checks it).
// Official domains verified 28 Oct 2026; subdomains count as official.
class _Brand {
  final String name;
  final List<String> text; // words naming the brand in a message
  final List<String> host; // substrings imitating it in a link's host
  final List<String> domains;
  const _Brand(this.name, this.text, this.host, this.domains);
}

const _brands = [
  _Brand('FNB', ['fnb', 'first national bank'], ['fnb', 'firstnationalbank'],
      ['fnb.co.za']),
  _Brand('Absa', ['absa'], ['absa'], ['absa.co.za', 'absa.africa']),
  _Brand('Standard Bank', ['standard bank', 'standardbank'], ['standardbank'],
      ['standardbank.co.za', 'standardbank.com']),
  _Brand('Capitec', ['capitec'], ['capitec'],
      ['capitecbank.co.za', 'capitec.co.za']),
  _Brand('Nedbank', ['nedbank'], ['nedbank'], ['nedbank.co.za']),
  _Brand('TymeBank', ['tymebank', 'tyme bank', 'gotyme'], ['tymebank', 'gotyme'],
      ['tymebank.co.za', 'gotyme.co.za']),
  _Brand('SARS', ['sars', 'efiling', 'e-filing'], ['sars', 'efiling'],
      ['sars.gov.za', 'sarsefiling.co.za']),
  _Brand('SASSA', ['sassa'], ['sassa'], ['sassa.gov.za']),
  _Brand('NSFAS', ['nsfas'], ['nsfas'], ['nsfas.org.za']),
  _Brand('SA Post Office', ['post office', 'postoffice', 'sapo'], ['postoffice'],
      ['postoffice.co.za']),
  _Brand('The Courier Guy', ['courier guy', 'courierguy'], ['courierguy'],
      ['thecourierguy.co.za']),
  _Brand('PostNet', ['postnet'], ['postnet'], ['postnet.co.za']),
  _Brand('Vodacom', ['vodacom'], ['vodacom'], ['vodacom.co.za', 'vodacom.com']),
  _Brand('MTN', ['mtn'], ['mtn'], ['mtn.co.za', 'mtn.com']),
  _Brand('Telkom', ['telkom'], ['telkom'], ['telkom.co.za']),
];

final _schemeRe = RegExp(r'^[a-z][a-z0-9+.-]*://', caseSensitive: false);

String _hostOf(String link) {
  final l = link.replaceFirst(RegExp(r'''[.,;:!?)"']+$'''), '');
  final url = _schemeRe.hasMatch(l) ? l : 'http://$l';
  return (Uri.tryParse(url)?.host ?? '').toLowerCase();
}

bool _onDomain(String host, List<String> domains) =>
    domains.any((d) => host == d || host.endsWith('.$d'));

/// Port of brand_rule() in ml/features.py: at most one brand flag (lookalike
/// first), and only when the message contains a link.
(String, int)? _brandRule(String text) {
  final hosts = _linkRe
      .allMatches(text)
      .map((m) => _hostOf(m.group(0)!))
      .where((h) => h.isNotEmpty)
      .toList();
  if (hosts.isEmpty) return null;
  for (final host in hosts) {
    final compact = host.replaceAll('-', '');
    for (final b in _brands) {
      if (b.host.any(compact.contains) && !_onDomain(host, b.domains)) {
        return ("Link imitates ${b.name} but is not ${b.name}'s official website", 30);
      }
    }
  }
  final prose = text.replaceAll(_linkRe, ' '); // a name inside a link is not a mention
  for (final b in _brands) {
    final named = b.text.any((k) =>
        RegExp('\\b${RegExp.escape(k)}\\b', caseSensitive: false).hasMatch(prose));
    if (named && !hosts.any((h) => _onDomain(h, b.domains))) {
      return ('Mentions ${b.name} but the link leads somewhere else', 20);
    }
  }
  return null;
}

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

  final brand = _brandRule(text);
  if (brand != null) check(true, brand.$2, brand.$1);
  check(_linkRe.hasMatch(text), 10, 'Contains a link');
  check(_shortenerRe.hasMatch(text), 20, 'Shortened link hides destination');
  check(_ipUrlRe.hasMatch(text), 25, 'Link uses a raw IP address');
  check(_urgency.any(t.contains), 15, 'Urgent or pressuring language');
  check(_impersonation.any(t.contains), 15, 'References trusted institution');
  check(_prize.any(t.contains), 15, 'Promises a prize or reward');
  check(_credentials.any(t.contains), 20, 'Asks for credentials or PIN');

  return LocalRuleResult(score.clamp(0, 100), flags);
}
