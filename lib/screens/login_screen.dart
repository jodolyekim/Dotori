import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dotori_client/services/auth_service.dart';
import 'package:dotori_client/screens/register_screen.dart';
import 'package:dotori_client/screens/home_screen.dart';
import 'package:dotori_client/widgets/dotori_button.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _auth = AuthService();
  final _id = TextEditingController();
  final _pw = TextEditingController();

  bool _loading = false;
  bool _rememberId = true;
  bool _autoLogin = true; // 기본 ON 권장 (개발 편의)

  String? _error;

  @override
  void initState() {
    super.initState();
    _restorePrefs();
  }

  Future<void> _restorePrefs() async {
    final sp = await SharedPreferences.getInstance();
    final saved = sp.getString('saved_username') ?? '';
    final auto = sp.getBool('auto_login') ?? true;
    setState(() {
      _id.text = saved;
      _rememberId = saved.isNotEmpty;
      _autoLogin = auto;
    });
  }

  Future<void> _login() async {
    FocusScope.of(context).unfocus();
    if (_id.text.trim().isEmpty || _pw.text.isEmpty) {
      setState(() => _error = '아이디/비밀번호를 입력해주세요.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final ok = await _auth.login(_id.text.trim(), _pw.text);
      if (!mounted) return;
      if (ok) {
        // 아이디 저장 / 자동로그인 설정 반영
        final sp = await SharedPreferences.getInstance();
        if (_rememberId) {
          await sp.setString('saved_username', _id.text.trim());
        } else {
          await sp.remove('saved_username');
        }
        await sp.setBool('auto_login', _autoLogin);

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('로그인 성공')),
        );
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      } else {
        setState(() => _error = '로그인 실패: 아이디/비밀번호를 확인하세요.');
      }
    } catch (e) {
      setState(() => _error = '로그인 오류: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dense = const EdgeInsets.symmetric(vertical: 10);
    return Scaffold(
      appBar: AppBar(title: const Text('도토리 로그인')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _id,
              decoration: const InputDecoration(labelText: '아이디'),
              textInputAction: TextInputAction.next,
              onSubmitted: (_) => FocusScope.of(context).nextFocus(),
            ),
            TextField(
              controller: _pw,
              decoration: const InputDecoration(labelText: '비밀번호'),
              obscureText: true,
              onSubmitted: (_) => _login(),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _rememberId,
                    onChanged: (v) => setState(() => _rememberId = v ?? false),
                    title: const Text('아이디 저장'),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                ),
                Expanded(
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _autoLogin,
                    onChanged: (v) => setState(() => _autoLogin = v),
                    title: const Text('자동 로그인'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            DotoriButton(text: '로그인', loading: _loading, onPressed: _login),
            TextButton(
              onPressed: _loading
                  ? null
                  : () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const RegisterScreen()),
                      ),
              child: const Text('회원가입'),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
          ],
        ),
      ),
    );
  }
}
