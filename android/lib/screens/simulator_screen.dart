/// Demo-safe message injector: runs realistic SA smishing samples (or custom
/// text) through the exact same pipeline as real incoming SMS.
library;

import 'package:flutter/material.dart';
import '../services/scan_store.dart';

const _samples = [
  ('SARS impersonation',
   'SARS eFiling: You have a pending refund of R3,450. Confirm your ID '
   'number at http://sars-refunds.xyz/claim within 24 hours.'),
  ('Bank suspension scam',
   'URGENT: Your FNB account has been suspended. Verify now at '
   'http://bit.ly/fnb-secure or lose access.'),
  ('Prize lure',
   'Congratulations! You have WON R25,000 in the Vodacom lottery. '
   'Claim at www.vcm-prize.xyz'),
  ('Courier scam',
   'Your parcel is held at customs. Pay the R45 release fee at '
   'http://196.23.155.8/track to avoid return.'),
  ('SASSA grant scam',
   'SASSA: Your grant payment failed. Update your details at '
   'sassa-verify.co.za/login to receive R2,090.'),
  ('Legitimate message',
   'Hey, are we still on for lunch tomorrow at 1?'),
  ('Legitimate bank notice',
   'FNB: R150.00 paid to Checkers from cheq acc. Ref 4521. '
   'Query? Call 087 575 9404.'),
];

class SimulatorScreen extends StatefulWidget {
  const SimulatorScreen({super.key});
  @override
  State<SimulatorScreen> createState() => _SimulatorScreenState();
}

class _SimulatorScreenState extends State<SimulatorScreen> {
  final _controller = TextEditingController();
  bool _busy = false;

  Future<void> _analyze(String text) async {
    if (text.trim().isEmpty || _busy) return;
    setState(() => _busy = true);
    await ScanStore.instance.process(text.trim(), 'SIMULATOR', 'simulated');
    setState(() => _busy = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Analyzed — see result on the Home tab')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Simulate an incoming SMS',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text('Runs through the exact same detection pipeline as a '
            'real message: local heuristics first, then cloud hybrid scoring.'),
        const SizedBox(height: 16),
        TextField(
          controller: _controller,
          maxLines: 4,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'Type or paste a message to analyze...',
          ),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          icon: _busy
              ? const SizedBox(
                  width: 16, height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.search),
          label: const Text('Analyze'),
          onPressed: _busy ? null : () => _analyze(_controller.text),
        ),
        const Divider(height: 32),
        Text('Sample messages',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        ..._samples.map((s) => Card(
              child: ListTile(
                title: Text(s.$1),
                subtitle:
                    Text(s.$2, maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: const Icon(Icons.play_arrow),
                onTap: () => _analyze(s.$2),
              ),
            )),
      ],
    );
  }
}
