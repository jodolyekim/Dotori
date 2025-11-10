import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dotori_client/services/auth_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _meText;
  String? _error;
  bool _loading = false;

  Future<void> _loadMe() async {
    setState(() {
      _loading = true;
      _error = null;
      _meText = null;
    });
    try {
      final me = await AuthService().me();
      setState(() => _meText = me.toString());
    } catch (e) {
      setState(() => _error = '불러오기 실패: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    await AuthService().logout();
    // 자동로그인까지 끄고 싶다면 아래 주석 해제:
    // final sp = await SharedPreferences.getInstance();
    // await sp.setBool('auto_login', false);

    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(context, '/', (_) => false);
  }

  @override
  Widget build(BuildContext context) {
    final dense = const EdgeInsets.symmetric(vertical: 10);
    return Scaffold(
      appBar: AppBar(
        title: const Text('홈 (로그인됨)'),
        actions: [
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
            tooltip: '로그아웃',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            ElevatedButton(
              onPressed: _loading ? null : _loadMe,
              child: Padding(
                padding: dense,
                child: _loading
                    ? const SizedBox(
                        width: 22, height: 22, child: CircularProgressIndicator())
                    : const Text('/api/auth/me 호출'),
              ),
            ),
            const SizedBox(height: 16),
            if (_meText != null)
              Expanded(
                child: SingleChildScrollView(
                  child: Text(
                    _meText!,
                    style: const TextStyle(fontFamily: 'monospace'),
                  ),
                ),
              ),
            if (_error != null)
              Text(
                _error!,
                style: const TextStyle(color: Colors.red),
              ),
          ],
        ),
      ),
    );
  }
}
