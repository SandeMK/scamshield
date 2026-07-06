/// FR-08 / US-05: in-app analytics dashboard — scan counts, risk-level
/// breakdown, and report summary.
library;

import 'package:flutter/material.dart';
import '../services/scan_store.dart';
import '../util.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = ScanStore.instance;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final byClass = store.byClassification;
        final total = store.totalScans;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(children: [
              _StatCard(label: 'Messages scanned', value: '$total'),
              const SizedBox(width: 12),
              _StatCard(
                  label: 'Threats caught',
                  value: '${store.threatsCaught}',
                  color: Colors.red[700]),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              _StatCard(label: 'Reports sent', value: '${store.reportsSent}'),
              const SizedBox(width: 12),
              _StatCard(
                  label: 'Offline scans',
                  value: '${store.scans.where((s) => s.offline).length}'),
            ]),
            const SizedBox(height: 24),
            Text('Detections by risk level',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (total == 0)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 32),
                child: Column(
                  children: [
                    Icon(Icons.insights_outlined, size: 64,
                        color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.35)),
                    const SizedBox(height: 12),
                    Text('No data yet',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 6),
                    Text('Scan a message on the Scans tab to see stats here.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  ],
                ),
              )
            else
              ...byClass.entries.map((e) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(children: [
                      SizedBox(
                          width: 110,
                          child: Text(classificationLabel(e.key),
                              style: const TextStyle(fontSize: 12))),
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: e.value / total,
                            minHeight: 14,
                            color: classificationColor(e.key),
                            backgroundColor: Colors.grey[200],
                          ),
                        ),
                      ),
                      SizedBox(
                          width: 32,
                          child: Text(' ${e.value}',
                              style: const TextStyle(fontSize: 12))),
                    ]),
                  )),
          ],
        );
      },
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  const _StatCard({required this.label, required this.value, this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(children: [
            Text(value,
                style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: color)),
            Text(label, style: const TextStyle(fontSize: 12)),
          ]),
        ),
      ),
    );
  }
}
