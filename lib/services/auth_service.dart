import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dotori_client/services/api_client.dart';

class AuthService {
  /// 회원가입 (이름/전화/인증토큰 포함)
  Future<bool> register({
    required String username,
    required String email,
    required String password,
    required String name,
    required String phone,
    required String phoneVerifiedToken,
  }) async {
    final res = await ApiClient.postJson('/api/auth/register/', {
      'username': username,
      'email': email,
      'password': password,
      'name': name,
      'phone': phone,
      'phone_verified_token': phoneVerifiedToken,
    });
    return res.statusCode == 201;
  }

  /// 아이디 중복확인
  Future<bool> checkUsernameAvailable(String username) async {
    final u = username.trim();
    if (u.isEmpty) return false;
    final res = await ApiClient.get('/api/auth/check-username/?username=$u');
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return data['available'] == true;
    }
    if (res.statusCode == 409) return false;
    throw Exception('아이디 중복확인 실패 (${res.statusCode})');
  }

  /// 휴대폰 인증번호 발송
  Future<int> sendPhoneCode(String phone) async {
    // 성공 시 재전송 쿨다운(초) 반환
    final res = await ApiClient.postJson('/api/auth/phone/send_code/', {
      'phone': phone,
    });
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return (data['cooldown'] as num?)?.toInt() ?? 60;
    }
    if (res.statusCode == 429) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return (data['cooldown'] as num?)?.toInt() ?? 60;
    }
    throw Exception('인증번호 전송 실패 (${res.statusCode})');
  }

  /// 휴대폰 인증번호 검증 → phone_verified_token 반환
  Future<String> verifyPhoneCode({
    required String phone,
    required String code,
  }) async {
    final res = await ApiClient.postJson('/api/auth/phone/verify_code/', {
      'phone': phone,
      'code': code,
    });
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final token = data['phone_verified_token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('인증 토큰 수신 실패');
      }
      return token;
    }
    final msg = res.body.isNotEmpty ? res.body : '휴대폰 인증 실패';
    throw Exception(msg);
  }

  /// 로그인 성공 시 access/refresh 저장
  Future<bool> login(String username, String password) async {
    final res = await ApiClient.postJson('/api/auth/token/', {
      'username': username,
      'password': password,
    });
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final access = data['access'] as String?;
      final refresh = data['refresh'] as String?;
      if (access == null || refresh == null) return false;

      final sp = await SharedPreferences.getInstance();
      await sp.setString('access_token', access);
      await sp.setString('refresh_token', refresh);
      return true;
    }
    return false;
  }

  /// 앱 시작 시 자동로그인 시도
  Future<bool> autoLoginIfPossible() async {
    final sp = await SharedPreferences.getInstance();
    final auto = sp.getBool('auto_login') ?? false;
    final refresh = sp.getString('refresh_token') ?? '';
    if (!auto || refresh.isEmpty) return false;

    final res = await ApiClient.postJson('/api/auth/token/refresh/', {
      'refresh': refresh,
    });
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final newAccess = data['access'] as String?;
      if (newAccess == null || newAccess.isEmpty) return false;
      await sp.setString('access_token', newAccess);
      return true;
    }
    return false;
  }

  Future<Map<String, dynamic>?> me() async {
    final res = await ApiClient.get('/api/auth/me/', auth: true);
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<void> logout() async {
    final sp = await SharedPreferences.getInstance();
    await sp.remove('access_token');
    await sp.remove('refresh_token');
  }

  Future<bool> isLoggedIn() async {
    final sp = await SharedPreferences.getInstance();
    return (sp.getString('access_token') ?? '').isNotEmpty;
  }
}
