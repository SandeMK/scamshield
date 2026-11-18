/// Check tab: paste any message (SMS, WhatsApp, email...) and score it
/// through the exact same pipeline as real incoming SMS. Pasted text is
/// tagged 'pasted'; the demo samples below it (FR-12 message simulation)
/// stay tagged 'simulated', so a real user's message is never labelled as
/// a simulation.
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

class CheckScreen extends StatefulWidget {
  const CheckScreen({super.key});
  @override
  State<CheckScreen> createState() => _CheckScreenState();
}

class _CheckScreenState extends State<CheckScreen> {
  final _controller = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _check(String text,
      {required String sender, required String source}) async {
    if (text.trim().isEmpty || _busy) return;
    setState(() => _busy = true);
    await ScanStore.instance.process(text.trim(), sender, source);
    if (!mounted) return;
    setState(() => _busy = false);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Checked. See the result on the Scans tab.')));
  }

  void _checkPasted() =>
      _check(_controller.text, sender: 'PASTED', source: 'pasted');

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Check a message',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text('Paste a message you\'re unsure about, from SMS, '
            'WhatsApp, email or anywhere else. It is checked exactly like '
            'an incoming SMS.'),
        const SizedBox(height: 16),
        TextField(
          controller: _controller,
          maxLines: 4,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'Paste or type the message here...',
          ),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          icon: _busy
              ? const SizedBox(
                  width: 16, height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.search),
          label: const Text('Check message'),
          onPressed: _busy ? null : _checkPasted,
        ),
        const SizedBox(height: 16),
        // FR-12: demo samples, collapsed so they don't crowd the real use.
        Card(
          clipBehavior: Clip.antiAlias,
          child: ExpansionTile(
            leading: const Icon(Icons.science_outlined),
            title: const Text('Try a sample message'),
            subtitle: const Text('Demo messages, tagged "simulated"'),
            children: _samples
                .map((s) => ListTile(
                      title: Text(s.$1),
                      subtitle: Text(s.$2,
                          maxLines: 2, overflow: TextOverflow.ellipsis),
                      trailing: const Icon(Icons.play_arrow),
                      onTap: () => _check(s.$2,
                          sender: 'SIMULATOR', source: 'simulated'),
                    ))
                .toList(),
          ),
        ),
      ],
    );
  }
}
