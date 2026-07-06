/// ScamShield — mobile-first smishing detection (ISJ107V).
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/dashboard_screen.dart';
import 'screens/home_screen.dart';
import 'screens/permission_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/simulator_screen.dart';
import 'services/scan_store.dart';
import 'services/sms_channel.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final firstLaunch = prefs.getBool('permission_explained') != true;
  runApp(ScamShieldApp(firstLaunch: firstLaunch));
}

class ScamShieldApp extends StatefulWidget {
  final bool firstLaunch;
  const ScamShieldApp({super.key, required this.firstLaunch});

  @override
  State<ScamShieldApp> createState() => _ScamShieldAppState();
}

class _ScamShieldAppState extends State<ScamShieldApp> {
  late bool _showPermission;

  @override
  void initState() {
    super.initState();
    _showPermission = widget.firstLaunch;
  }

  void _onPermissionDone() => setState(() => _showPermission = false);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ScamShield',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1B5E20)),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1B5E20),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.light,
      home: _showPermission
          ? PermissionScreen(onDone: _onPermissionDone)
          : const RootScaffold(),
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
    _smsSub = SmsChannel.stream().listen(
      (sms) => ScanStore.instance.process(sms.body, sms.sender, 'sms'),
      onError: (_) {},
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
          NavigationDestination(
              icon: Icon(Icons.shield_outlined), label: 'Scans'),
          NavigationDestination(
              icon: Icon(Icons.science_outlined), label: 'Simulate'),
          NavigationDestination(
              icon: Icon(Icons.insights_outlined), label: 'Dashboard'),
          NavigationDestination(
              icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }
}