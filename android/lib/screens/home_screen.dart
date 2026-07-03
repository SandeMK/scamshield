/// Home: colour-coded scan cards (FR-04) with detail sheet showing
/// explanation codes (US-02) and report actions (FR-05, US-03/04).
library;

import 'package:flutter/material.dart';
import '../models.dart';
import '../services/scan_store.dart';
import '../util.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = ScanStore.instance;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        if (store.scans.isEmpty) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Text(
                'No messages scanned yet.\n\nIncoming SMS will appear here '
                'automatically, or use the Simulate tab to inject a test message.',
                textAlign: TextAlign.center,
              ),
            ),
          );
        }
        return ListView.builder(
          itemCount: store.scans.length,
          itemBuilder: (context, i) => _ScanCard(scan: store.scans[i]),
        );
      },
    );
  }
}

class _ScanCard extends StatelessWidget {
  final Scan scan;
  const _ScanCard({required this.scan});

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
        title: Text(scan.text,
            maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Text(
            '${classificationLabel(label)} · ${scan.sender}'
            '${scan.offline ? ' · cloud offline, local result' : ''}'
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

class _ScanDetail extends StatelessWidget {
  final Scan scan;
  const _ScanDetail({required this.scan});

  @override
  Widget build(BuildContext context) {
    final r = scan.result;
    final label = r?.classification ?? (scan.offline ? 'OFFLINE' : 'PENDING');
    final color = classificationColor(label);

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.65,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.all(20),
        children: [
          Row(children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: color,
              child: Text('${r?.riskScore ?? scan.localScore}',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(classificationLabel(label),
                      style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: color)),
                  if (r != null)
                    Text('ML confidence ${(r.mlConfidence * 100).toStringAsFixed(0)}%'
                        ' · rules ${r.ruleSubScore}/100'),
                ],
              ),
            ),
          ]),
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
                    'heuristic checks only (results may be less accurate).',
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
            const SizedBox(height: 8),
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
