/// ScamShield — mobile-first smishing detection (ISJ107V).
library;

import 'dart:async';
import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';
import 'screens/home_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/simulator_screen.dart';
import 'services/scan_store.dart';
import 'services/sms_channel.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ScamShieldApp());
}

class ScamShieldApp extends StatelessWidget {
  const ScamShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ScamShield',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1B5E20)),
        useMaterial3: true,
      ),
      home: const RootScaffold(),
    );
  }
}

class RootScaffold extends StatefulWidget {
  const RootScaffold({super.key});
  @override
  State<RootScaffold> createState() => _RootScaffoldState();
}

class _RootScaffoldState extends State<RootScaffold> {
  int _index = 0;
  StreamSubscription? _smsSub;

  @override
  void initState() {
    super.initState();
    ScanStore.instance.load();
    // Real incoming SMS via the Android platform channel (FR-01).
    _smsSub = SmsChannel.stream().listen(
      (sms) => ScanStore.instance.process(sms.body, sms.sender, 'sms'),
      onError: (_) {}, // permission denied or unsupported: simulator still works
    );
  }

  @override
  void dispose() {
    _smsSub?.cancel();
    super.dispose();
  }

  static const _screens = [
    HomeScreen(),
    SimulatorScreen(),
    DashboardScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ScamShield'), centerTitle: true),
      body: _screens[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.shield_outlined), label: 'Scans'),
          NavigationDestination(icon: Icon(Icons.science_outlined), label: 'Simulate'),
          NavigationDestination(icon: Icon(Icons.insights_outlined), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }
}
