/// Settings: API base URL + API key, with a connectivity check.
library;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';
import '../services/device_id.dart';
import '../services/guardian_channel.dart';
import '../services/scan_store.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _url = TextEditingController();
  final _key = TextEditingController();
  final _guardianContact = TextEditingController();
  String _status = '';
  String _guardianStatus = '';
  bool _guardianPermissionGranted = false;

  // UC-13 Manage Profile & Notifications (FR-14/15/16)
  String? _deviceId;
  bool _profileLoading = true;
  bool _hasProfile = false;
  final _displayName = TextEditingController();
  final _profileEmail = TextEditingController();
  String _profileStatus = '';

  String _alertThreshold = 'MEDIUM_RISK';
  bool _retroactiveUpdates = true;
  bool _reportOutcomes = true;
  String _digestFrequency = 'off';
  String _notifStatus = '';

  final _recoveryEmail = TextEditingController();
  final _recoveryCode = TextEditingController();
  bool _recoveryCodeSent = false;
  String _recoveryStatus = '';

  @override
  void initState() {
    super.initState();
    SharedPreferences.getInstance().then((prefs) {
      setState(() {
        _url.text = prefs.getString('baseUrl') ?? ApiClient.defaultBaseUrl;
        _key.text = prefs.getString('apiKey') ?? ApiClient.defaultApiKey;
        _guardianContact.text = prefs.getString('guardianContact') ?? '';
      });
    });
    GuardianChannel.hasPermission().then((granted) {
      if (mounted) setState(() => _guardianPermissionGranted = granted);
    });
    _loadProfile();
  }

  @override
  void dispose() {
    _url.dispose();
    _key.dispose();
    _guardianContact.dispose();
    _displayName.dispose();
    _profileEmail.dispose();
    _recoveryEmail.dispose();
    _recoveryCode.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    _deviceId = await DeviceId.get();
    try {
      final profile = await ApiClient().getProfile(_deviceId!);
      if (profile != null) _applyProfile(profile);
    } catch (_) {} // offline: fall through to the create-profile form
    if (mounted) setState(() => _profileLoading = false);
  }

  void _applyProfile(Map<String, dynamic> profile) {
    _hasProfile = true;
    _displayName.text = profile['display_name'] ?? '';
    _profileEmail.text = profile['email'] ?? '';
    final prefs = (profile['notification_prefs'] as Map?) ?? {};
    _alertThreshold = prefs['alert_threshold'] ?? 'MEDIUM_RISK';
    _retroactiveUpdates = prefs['retroactive_updates'] ?? true;
    _reportOutcomes = prefs['report_outcomes'] ?? true;
    _digestFrequency = prefs['digest_frequency'] ?? 'off';
  }

  // FR-14: opt-in from Settings, independent of the anonymous device_id
  // generated at first launch. A profile created after weeks of anonymous
  // use inherits the totals already associated with this device.
  Future<void> _saveProfile() async {
    if (_deviceId == null) return;
    setState(() => _profileStatus = 'Saving...');
    try {
      final profile = await ApiClient().createOrUpdateProfile(
        deviceId: _deviceId!,
        displayName:
            _displayName.text.trim().isEmpty ? null : _displayName.text.trim(),
        email: _profileEmail.text.trim().isEmpty
            ? null
            : _profileEmail.text.trim(),
        totalScans: _hasProfile ? null : ScanStore.instance.totalScans,
        totalReports: _hasProfile ? null : ScanStore.instance.reportsSent,
      );
      setState(() {
        _applyProfile(profile);
        _profileStatus = 'Profile saved.';
      });
    } catch (e) {
      setState(() => _profileStatus = 'Could not save profile: $e');
    }
  }

  // FR-15: only ever shown for a device with an active profile.
  Future<void> _saveNotificationPrefs() async {
    if (_deviceId == null) return;
    setState(() => _notifStatus = 'Saving...');
    try {
      await ApiClient().updateNotificationPrefs(
        deviceId: _deviceId!,
        alertThreshold: _alertThreshold,
        retroactiveUpdates: _retroactiveUpdates,
        reportOutcomes: _reportOutcomes,
        digestFrequency: _digestFrequency,
      );
      setState(() => _notifStatus = 'Preferences saved.');
    } catch (e) {
      setState(() => _notifStatus = 'Could not save preferences: $e');
    }
  }

  // FR-16: request the emailed code, then verify it re-links this device.
  Future<void> _sendRecoveryCode() async {
    if (_recoveryEmail.text.trim().isEmpty) return;
    setState(() => _recoveryStatus = 'Sending code...');
    try {
      await ApiClient().requestRecoveryCode(_recoveryEmail.text.trim());
      setState(() {
        _recoveryCodeSent = true;
        _recoveryStatus = 'Code sent — check that inbox for a 6-digit code.';
      });
    } catch (e) {
      setState(() => _recoveryStatus = 'Could not send code: $e');
    }
  }

  Future<void> _verifyRecoveryCode() async {
    if (_deviceId == null) return;
    setState(() => _recoveryStatus = 'Verifying...');
    try {
      final profile = await ApiClient().verifyRecoveryCode(
        email: _recoveryEmail.text.trim(),
        code: _recoveryCode.text.trim(),
        deviceId: _deviceId!,
      );
      setState(() {
        _applyProfile(profile);
        _recoveryStatus = 'Profile restored to this device.';
      });
    } catch (e) {
      setState(() => _recoveryStatus = 'Invalid or expired code.');
    }
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

  // FR-09: opt-in from Settings only — never requested at first launch.
  Future<void> _saveGuardianContact() async {
    final number = _guardianContact.text.trim();
    final prefs = await SharedPreferences.getInstance();

    if (number.isEmpty) {
      await prefs.remove('guardianContact');
      setState(() => _guardianStatus = 'Guardian Alert disabled.');
      return;
    }

    if (!_guardianPermissionGranted) {
      final proceed = await _showGuardianExplainer();
      if (proceed != true) return;
      final granted = await GuardianChannel.requestPermission();
      if (!mounted) return;
      setState(() => _guardianPermissionGranted = granted);
      if (!granted) {
        setState(() => _guardianStatus =
            'SMS permission denied — Guardian Alert will not send until it is granted.');
        return;
      }
    }

    await prefs.setString('guardianContact', number);
    setState(() => _guardianStatus =
        'Saved. $number will be texted automatically if a message scores CRITICAL.');
  }

  Future<bool?> _showGuardianExplainer() {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Send SMS permission'),
        content: const Text(
          'ScamShield needs permission to send SMS so it can automatically '
          'text your trusted contact if a message you receive is classified '
          'CRITICAL. No message content is sent anywhere else, and this '
          'contact number is stored only on this device.',
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Continue')),
        ],
      ),
    );
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
        const Divider(height: 40),
        Text('Guardian Alert', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text(
          'Optional. If a message you receive is classified CRITICAL, '
          'ScamShield automatically texts this contact — no tapping needed. '
          'The number is stored only on this device, never sent to the cloud.',
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _guardianContact,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(
              labelText: 'Trusted contact number',
              hintText: 'e.g. 0821234567',
              border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        FilledButton(
            onPressed: _saveGuardianContact,
            child: const Text('Save trusted contact')),
        const SizedBox(height: 12),
        Text(_guardianStatus),
        const Divider(height: 40),
        Text('Profile (optional)', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text(
          'Independent of anonymous scanning — create a profile only if you '
          'want notification preferences or the ability to recover your '
          'activity on a new install. Everything else works without one.',
        ),
        const SizedBox(height: 16),
        if (_profileLoading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: LinearProgressIndicator(),
          )
        else ...[
          TextField(
            controller: _displayName,
            decoration: const InputDecoration(
                labelText: 'Display name (optional)',
                border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _profileEmail,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
                labelText: 'Recovery email (optional)',
                border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          FilledButton(
              onPressed: _saveProfile,
              child: Text(_hasProfile ? 'Update profile' : 'Create profile')),
          const SizedBox(height: 12),
          Text(_profileStatus),
          if (_hasProfile) ...[
            const Divider(height: 40),
            Text('Notification preferences',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _alertThreshold,
              decoration: const InputDecoration(
                  labelText: 'Alert me at or above',
                  border: OutlineInputBorder()),
              items: const [
                DropdownMenuItem(value: 'SAFE', child: Text('Safe')),
                DropdownMenuItem(value: 'LOW_RISK', child: Text('Low risk')),
                DropdownMenuItem(
                    value: 'MEDIUM_RISK', child: Text('Medium risk')),
                DropdownMenuItem(value: 'HIGH_RISK', child: Text('High risk')),
                DropdownMenuItem(value: 'CRITICAL', child: Text('Critical')),
              ],
              onChanged: (v) => setState(() => _alertThreshold = v!),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Retroactive re-classification alerts'),
              value: _retroactiveUpdates,
              onChanged: (v) => setState(() => _retroactiveUpdates = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Report-outcome alerts'),
              value: _reportOutcomes,
              onChanged: (v) => setState(() => _reportOutcomes = v),
            ),
            const SizedBox(height: 4),
            DropdownButtonFormField<String>(
              initialValue: _digestFrequency,
              decoration: const InputDecoration(
                  labelText: 'Digest frequency', border: OutlineInputBorder()),
              items: const [
                DropdownMenuItem(value: 'off', child: Text('Off')),
                DropdownMenuItem(value: 'daily', child: Text('Daily')),
                DropdownMenuItem(value: 'weekly', child: Text('Weekly')),
              ],
              onChanged: (v) => setState(() => _digestFrequency = v!),
            ),
            const SizedBox(height: 12),
            FilledButton(
                onPressed: _saveNotificationPrefs,
                child: const Text('Save preferences')),
            const SizedBox(height: 12),
            Text(_notifStatus),
          ] else ...[
            const Divider(height: 40),
            Text('Recover a profile',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            const Text(
              'Already have a profile from another install? Enter its '
              'recovery email to get a one-time code.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _recoveryEmail,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                  labelText: 'Recovery email', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            FilledButton(
                onPressed: _sendRecoveryCode,
                child: const Text('Send recovery code')),
            if (_recoveryCodeSent) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _recoveryCode,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: '6-digit code', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              FilledButton(
                  onPressed: _verifyRecoveryCode,
                  child: const Text('Verify and restore')),
            ],
            const SizedBox(height: 12),
            Text(_recoveryStatus),
          ],
        ],
      ],
    );
  }
}
