/// One-time first-launch privacy explainer shown before the SMS permission
/// dialog. Explains privacy-by-design: messages scanned on-device,
/// only SHA-256 hashes stored server-side. FR-01.
library;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class PermissionScreen extends StatelessWidget {
  final VoidCallback onDone;
  const PermissionScreen({super.key, required this.onDone});

  Future<void> _proceed() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('permission_explained', true);
    onDone();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.shield, size: 96, color: scheme.primary),
              const SizedBox(height: 24),
              Text(
                'ScamShield protects you',
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              const Text(
                'ScamShield reads incoming SMS to detect smishing (SMS phishing) '
                'attempts in real time.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              const _PrivacyPoint(
                icon: Icons.phone_android,
                text:
                    'Messages are scored on your device first using local rules.',
              ),
              const _PrivacyPoint(
                icon: Icons.lock_outline,
                text:
                    'Only a SHA-256 hash of suspicious indicators is ever sent '
                    'to the cloud — your message text stays private.',
              ),
              const _PrivacyPoint(
                icon: Icons.storage_outlined,
                text: 'No message content is stored on any server.',
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  icon: const Icon(Icons.security),
                  label: const Text('Enable protection'),
                  onPressed: _proceed,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Next, Android will ask for SMS permission.',
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PrivacyPoint extends StatelessWidget {
  final IconData icon;
  final String text;
  const _PrivacyPoint({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}