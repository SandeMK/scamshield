/// Status line shown directly under a form action (Settings sections, the
/// scan detail sheet's report buttons). Inline rather than a SnackBar
/// because the outcome belongs to that one action, stays visible while the
/// user fixes the input, and the scan sheet sits above the root Scaffold
/// where a SnackBar would be hidden.
library;

import 'package:flutter/material.dart';

enum StatusKind { busy, success, error }

class InlineStatus {
  final StatusKind kind;
  final String text;
  const InlineStatus.busy(this.text) : kind = StatusKind.busy;
  const InlineStatus.success(this.text) : kind = StatusKind.success;
  const InlineStatus.error(this.text) : kind = StatusKind.error;

  bool get isBusy => kind == StatusKind.busy;
}

class InlineStatusLine extends StatelessWidget {
  final InlineStatus? status;
  const InlineStatusLine(this.status, {super.key});

  @override
  Widget build(BuildContext context) {
    final s = status;
    if (s == null) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final (Widget icon, Color color) = switch (s.kind) {
      StatusKind.busy => (
          const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2)),
          scheme.onSurfaceVariant,
        ),
      StatusKind.success => (
          Icon(Icons.check_circle_outline, size: 18, color: Colors.green[700]),
          Colors.green[700]!,
        ),
      StatusKind.error => (
          Icon(Icons.error_outline, size: 18, color: scheme.error),
          scheme.error,
        ),
    };
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(padding: const EdgeInsets.only(top: 1), child: icon),
          const SizedBox(width: 8),
          Expanded(child: Text(s.text, style: TextStyle(color: color))),
        ],
      ),
    );
  }
}
