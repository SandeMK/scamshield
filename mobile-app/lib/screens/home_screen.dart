/// Home: colour-coded scan cards (FR-04) with detail sheet showing
/// explanation codes (US-02) and report actions (FR-05, US-03/04).
library;

import 'dart:math';
import 'package:flutter/material.dart';
import '../models.dart';
import '../services/scan_store.dart';
import '../util.dart';

enum _Filter { all, suspicious, reported }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  _Filter _filter = _Filter.all;

  List<Scan> _filtered(List<Scan> scans) => switch (_filter) {
        _Filter.all => scans,
        _Filter.suspicious => scans
            .where((s) =>
                {'MEDIUM_RISK', 'HIGH_RISK', 'CRITICAL'}
                    .contains(s.result?.classification) ||
                (s.result == null && s.localScore >= 40))
            .toList(),
        _Filter.reported => scans.where((s) => s.reported).toList(),
      };

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: ScanStore.instance,
      builder: (context, _) {
        final scans = _filtered(ScanStore.instance.scans);
        return Column(
          children: [
            _FilterBar(
              current: _filter,
              onChanged: (f) => setState(() => _filter = f),
            ),
            Expanded(
              child: scans.isEmpty
                  ? _EmptyState(filter: _filter)
                  : ListView.builder(
                      itemCount: scans.length,
                      itemBuilder: (context, i) {
                        final scan = scans[i];
                        final isNew =
                            DateTime.now().difference(scan.timestamp).inSeconds < 5;
                        final card = _ScanCard(key: ValueKey(scan.id), scan: scan);
                        if (!isNew) return card;
                        return TweenAnimationBuilder<double>(
                          tween: Tween(begin: 0.0, end: 1.0),
                          duration: const Duration(milliseconds: 420),
                          curve: Curves.easeOut,
                          builder: (_, v, child) => Opacity(
                            opacity: v,
                            child: Transform.translate(
                              offset: Offset(0, 24 * (1 - v)),
                              child: child,
                            ),
                          ),
                          child: card,
                        );
                      },
                    ),
            ),
          ],
        );
      },
    );
  }
}

class _FilterBar extends StatelessWidget {
  final _Filter current;
  final ValueChanged<_Filter> onChanged;
  const _FilterBar({required this.current, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          _chip('All', _Filter.all),
          const SizedBox(width: 8),
          _chip('Suspicious+', _Filter.suspicious),
          const SizedBox(width: 8),
          _chip('Reported', _Filter.reported),
        ],
      ),
    );
  }

  Widget _chip(String label, _Filter value) => FilterChip(
        label: Text(label),
        selected: current == value,
        onSelected: (_) => onChanged(value),
        visualDensity: VisualDensity.compact,
      );
}

class _EmptyState extends StatelessWidget {
  final _Filter filter;
  const _EmptyState({required this.filter});

  @override
  Widget build(BuildContext context) {
    final (icon, title, body) = switch (filter) {
      _Filter.suspicious => (
          Icons.check_circle_outline,
          'No suspicious messages',
          'No medium-risk or higher messages scanned yet.',
        ),
      _Filter.reported => (
          Icons.flag_outlined,
          'No reports sent',
          'Use the report button on a scan to flag scams to the network.',
        ),
      _Filter.all => (
          Icons.shield_outlined,
          'No messages scanned yet',
          'Incoming SMS will appear here automatically, or use the Simulate tab '
              'to inject a test message.',
        ),
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 72,
                color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.4)),
            const SizedBox(height: 16),
            Text(title,
                style: Theme.of(context).textTheme.titleMedium,
                textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(body,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ],
        ),
      ),
    );
  }
}

class _ScanCard extends StatelessWidget {
  final Scan scan;
  const _ScanCard({super.key, required this.scan});

  @override
  Widget build(BuildContext context) {
    final label = scan.result?.classification ??
        (scan.offline ? 'OFFLINE' : 'PENDING');
    final color = classificationColor(label);
    final score = scan.result?.riskScore ?? scan.localScore;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      shape: RoundedRectangleBorder(
        side: BorderSide(color: color, width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color,
          child: Text('$score',
              style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.bold)),
        ),
        title: Text(scan.text, maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Text(
            '${classificationLabel(label)} · ${scan.sender}'
            '${scan.offline ? ' · cloud offline' : ''}'
            '${scan.source == 'simulated' ? ' · simulated' : ''}'),
        onTap: () => _showDetail(context),
      ),
    );
  }

  void _showDetail(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _ScanDetail(scan: scan),
    );
  }
}

// ── Scan detail sheet ────────────────────────────────────────────────────────

class _ScanDetail extends StatelessWidget {
  final Scan scan;
  const _ScanDetail({required this.scan});

  @override
  Widget build(BuildContext context) {
    final r = scan.result;
    final label = r?.classification ?? (scan.offline ? 'OFFLINE' : 'PENDING');
    final color = classificationColor(label);
    final score = r?.riskScore ?? scan.localScore;

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        children: [
          // Risk gauge
          Center(child: _RiskGauge(score: score, color: color)),
          Center(
            child: Text(classificationLabel(label),
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: color)),
          ),
          if (r != null)
            Center(
              child: Text(
                'ML ${(r.mlConfidence * 100).toStringAsFixed(0)}% · rules ${r.ruleSubScore}/100',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          const SizedBox(height: 16),
          Text(scan.text),
          const Divider(height: 32),
          Text('Why this was flagged',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (r != null)
            ...r.explanationCodes.map((c) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.info_outline, size: 20),
                  title: Text(c.detail),
                  subtitle: Text(c.code,
                      style: const TextStyle(fontSize: 11)),
                ))
          else ...[
            if (scan.offline)
              const Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: Text(
                    'Cloud scoring is temporarily offline — showing local '
                    'heuristic checks only.',
                    style: TextStyle(fontStyle: FontStyle.italic)),
              ),
            ...scan.localFlags.map((f) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.rule, size: 20),
                  title: Text(f),
                )),
          ],
          if (r != null) ...[
            const SizedBox(height: 4),
            Text('Model ${r.modelVersion}',
                style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 16),
          Row(children: [
            Expanded(
              child: FilledButton.icon(
                icon: const Icon(Icons.report),
                label: const Text('Report scam'),
                style: FilledButton.styleFrom(backgroundColor: Colors.red[700]),
                onPressed: scan.reported ? null : () => _report(context, 'scam'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                icon: const Icon(Icons.thumb_down_alt_outlined),
                label: const Text('False positive'),
                onPressed:
                    scan.reported ? null : () => _report(context, 'false_positive'),
              ),
            ),
          ]),
          if (scan.reported)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Report submitted — thank you for contributing.',
                  textAlign: TextAlign.center),
            ),
        ],
      ),
    );
  }

  Future<void> _report(BuildContext context, String type) async {
    final ok = await ScanStore.instance.report(scan, type);
    if (context.mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(ok
              ? 'Report submitted to the shared threat network'
              : 'Could not submit report — check your connection')));
    }
  }
}

// ── Animated risk gauge ───────────────────────────────────────────────────────

class _RiskGauge extends StatelessWidget {
  final int score;
  final Color color;
  const _RiskGauge({required this.score, required this.color});

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: score / 100),
      duration: const Duration(milliseconds: 900),
      curve: Curves.easeOut,
      builder: (_, value, __) => CustomPaint(
        size: const Size(160, 96),
        painter: _GaugePainter(value: value, color: color,
            background: Theme.of(context).colorScheme.surfaceContainerHighest),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double value;
  final Color color;
  final Color background;
  _GaugePainter({required this.value, required this.color, required this.background});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height * 0.92;
    final r = size.width * 0.44;
    final rect = Rect.fromCircle(center: Offset(cx, cy), radius: r);
    const strokeW = 12.0;

    canvas.drawArc(rect, pi, pi, false,
        Paint()
          ..color = background
          ..style = PaintingStyle.stroke
          ..strokeWidth = strokeW
          ..strokeCap = StrokeCap.round);

    if (value > 0) {
      canvas.drawArc(rect, pi, pi * value, false,
          Paint()
            ..color = color
            ..style = PaintingStyle.stroke
            ..strokeWidth = strokeW
            ..strokeCap = StrokeCap.round);
    }

    final tp = TextPainter(
      text: TextSpan(
        text: '${(value * 100).round()}',
        style: TextStyle(
            color: color, fontSize: 26, fontWeight: FontWeight.bold),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, Offset(cx - tp.width / 2, cy - tp.height - 6));
  }

  @override
  bool shouldRepaint(_GaugePainter old) =>
      old.value != value || old.color != color;
}
