/// Settings: API base URL + API key, with a connectivity check.
library;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _url = TextEditingController();
  final _key = TextEditingController();
  String _status = '';

  @override
  void initState() {
    super.initState();
    SharedPreferences.getInstance().then((prefs) {
      setState(() {
        _url.text = prefs.getString('baseUrl') ?? ApiClient.defaultBaseUrl;
        _key.text = prefs.getString('apiKey') ?? ApiClient.defaultApiKey;
      });
    });
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('baseUrl', _url.text.trim());
    await prefs.setString('apiKey', _key.text.trim());
    setState(() => _status = 'Saved. Checking connection...');
    try {
      final h = await ApiClient().health();
      setState(() => _status =
          'Connected — model ${h['model_version'] ?? '?'}, '
          'DB: ${h['db_connected'] ?? 'n/a'}');
    } catch (e) {
      setState(() => _status = 'Could not reach API: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Cloud API', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text('Use http://10.0.2.2:8000 for the Android emulator with a '
            'locally running API, or your deployed Render/Cloud Run URL.'),
        const SizedBox(height: 16),
        TextField(
            controller: _url,
            decoration: const InputDecoration(
                labelText: 'Base URL', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(
            controller: _key,
            decoration: const InputDecoration(
                labelText: 'API key', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        FilledButton(onPressed: _save, child: const Text('Save & test')),
        const SizedBox(height: 12),
        Text(_status),
      ],
    );
  }
}
