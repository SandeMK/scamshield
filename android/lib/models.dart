/// ScamShield data models — mirror the /api/v1 contract (Assignment 2 §12).
library;

class ExplanationCode {
  final String code;
  final String detail;
  ExplanationCode({required this.code, required this.detail});

  factory ExplanationCode.fromJson(Map<String, dynamic> j) =>
      ExplanationCode(code: j['code'] ?? '', detail: j['detail'] ?? '');
  Map<String, dynamic> toJson() => {'code': code, 'detail': detail};
}

class ScoreResult {
  final int riskScore;
  final String classification;
  final double mlConfidence;
  final int ruleSubScore;
  final List<ExplanationCode> explanationCodes;
  final String modelVersion;

  ScoreResult({
    required this.riskScore,
    required this.classification,
    required this.mlConfidence,
    required this.ruleSubScore,
    required this.explanationCodes,
    required this.modelVersion,
  });

  factory ScoreResult.fromJson(Map<String, dynamic> j) => ScoreResult(
        riskScore: (j['risk_score'] ?? 0).toInt(),
        classification: j['classification'] ?? 'SAFE',
        mlConfidence: (j['ml_confidence'] ?? 0.0).toDouble(),
        ruleSubScore: (j['rule_sub_score'] ?? 0).toInt(),
        explanationCodes: ((j['explanation_codes'] ?? []) as List)
            .map((e) => ExplanationCode.fromJson(e))
            .toList(),
        modelVersion: j['model_version'] ?? '',
      );

  Map<String, dynamic> toJson() => {
        'risk_score': riskScore,
        'classification': classification,
        'ml_confidence': mlConfidence,
        'rule_sub_score': ruleSubScore,
        'explanation_codes': explanationCodes.map((e) => e.toJson()).toList(),
        'model_version': modelVersion,
      };
}

class Scan {
  final String id;
  final String text;
  final String sender;
  final DateTime timestamp;
  final String source; // 'sms' | 'simulated'
  ScoreResult? result;
  bool offline; // NFR-08: cloud unreachable, local heuristics only
  int localScore; // FR-10 immediate local heuristic score
  List<String> localFlags;
  bool reported;

  Scan({
    required this.id,
    required this.text,
    required this.sender,
    required this.timestamp,
    required this.source,
    this.result,
    this.offline = false,
    this.localScore = 0,
    this.localFlags = const [],
    this.reported = false,
  });

  factory Scan.fromJson(Map<String, dynamic> j) => Scan(
        id: j['id'],
        text: j['text'],
        sender: j['sender'],
        timestamp: DateTime.parse(j['timestamp']),
        source: j['source'] ?? 'sms',
        result:
            j['result'] == null ? null : ScoreResult.fromJson(j['result']),
        offline: j['offline'] ?? false,
        localScore: j['localScore'] ?? 0,
        localFlags: List<String>.from(j['localFlags'] ?? []),
        reported: j['reported'] ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'text': text,
        'sender': sender,
        'timestamp': timestamp.toIso8601String(),
        'source': source,
        'result': result?.toJson(),
        'offline': offline,
        'localScore': localScore,
        'localFlags': localFlags,
        'reported': reported,
      };
}
