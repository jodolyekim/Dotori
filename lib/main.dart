import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/landing_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/home_screen.dart';

import 'services/auth_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const DotoriApp());
}

class DotoriApp extends StatefulWidget {
  const DotoriApp({super.key});

  @override
  State<DotoriApp> createState() => _DotoriAppState();
}

class _DotoriAppState extends State<DotoriApp> {
  bool _booting = true;
  bool _loggedIn = false;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    // 자동로그인 설정(true) && refresh 토큰 있으면 갱신 시도
    final ok = await AuthService().autoLoginIfPossible();
    _loggedIn = ok;
    if (mounted) setState(() => _booting = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF795548)),
      useMaterial3: true,
    );

    if (_booting) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: theme,
        home: const _BootScreen(),
      );
    }

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '도토리',
      theme: theme,
      // ✅ 홈 위젯을 항상 제공해서 null 경로가 없게 함
      home: _loggedIn ? const HomeScreen() : const LandingScreen(),
      routes: {
        '/login': (_) => const LoginScreen(),
        '/register': (_) => const RegisterScreen(),
        '/home': (_) => const HomeScreen(),
      },
    );
  }
}

class _BootScreen extends StatelessWidget {
  const _BootScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 12),
            Text('앱 준비 중...'),
          ],
        ),
      ),
    );
  }
}
