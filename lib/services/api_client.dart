import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dotori_client/config.dart';

/// 공통 HTTP 클라이언트
/// - Authorization: Bearer <access>
/// - 401 이면 refresh 토큰으로 1회 재발급 후 재시도
class ApiClient {
  static Uri _u(String path) => Uri.parse('${Config.baseUrl}$path');

  /// JSON POST (auth=true면 토큰 첨부, 401 시 자동 리프레시 후 1회 재시도)
  static Future<http.Response> postJson(
    String path,
    Map<String, dynamic> body, {
    bool auth = false,
  }) async {
    return _requestWithRetry(
      () async => http.post(_u(path),
          headers: await _headers(auth: auth), body: jsonEncode(body)),
      auth: auth,
    );
  }

  /// GET (auth=true면 토큰 첨부, 401 시 자동 리프레시 후 1회 재시도)
  static Future<http.Response> get(
    String path, {
    bool auth = false,
  }) async {
    return _requestWithRetry(
      () async => http.get(_u(path), headers: await _headers(auth: auth)),
      auth: auth,
    );
  }

  /// 내부: 요청 실행 + 401 처리
  static Future<http.Response> _requestWithRetry(
    Future<http.Response> Function() doRequest, {
    required bool auth,
  }) async {
    final first = await doRequest();
    if (!auth || first.statusCode != 401) return first;

    // 401 → refresh 시도
    final refreshed = await _refreshAccessToken();
    if (!refreshed) return first; // 갱신 실패 → 원 응답 반환

    // refresh 성공 → 다시 요청
    return await doRequest();
  }

  /// 헤더 생성 (auth=true면 access 토큰 포함)
  static Future<Map<String, String>> _headers({bool auth = false}) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (auth) {
      final sp = await SharedPreferences.getInstance();
      final token = sp.getString('access_token');
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  /// access 토큰을 refresh 토큰으로 갱신
  static Future<bool> _refreshAccessToken() async {
    try {
      final sp = await SharedPreferences.getInstance();
      final refresh = sp.getString('refresh_token');
      if (refresh == null || refresh.isEmpty) return false;

      final res = await http.post(
        _u('/api/auth/token/refresh/'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refresh}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final newAccess = data['access'] as String?;
        if (newAccess == null || newAccess.isEmpty) return false;
        await sp.setString('access_token', newAccess);
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }
}
