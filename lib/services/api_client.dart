import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dotori_client/config.dart';

/// 공통 HTTP 클라이언트
/// - Authorization: Bearer <access>
/// - 401이면 refresh 토큰으로 1회 갱신 후 재시도
class ApiClient {
  static Uri _u(String path) => Uri.parse('${Config.baseUrl}$path');

  /// JSON POST
  static Future<http.Response> postJson(
    String path,
    Map<String, dynamic> body, {
    bool auth = false,
  }) async {
    return _requestWithRetry(
      () async => http.post(
        _u(path),
        headers: await _headers(auth: auth),
        body: jsonEncode(body),
      ),
      auth: auth,
    );
  }

  /// GET
  static Future<http.Response> get(
    String path, {
    bool auth = false,
  }) async {
    return _requestWithRetry(
      () async => http.get(_u(path), headers: await _headers(auth: auth)),
      auth: auth,
    );
  }

  /// 멀티파트 POST (파일/이미지 업로드)
  static Future<http.StreamedResponse> postMultipart(
    String path, {
    Map<String, String>? fields,
    List<ApiMultipartFile>? files,
    bool auth = false,
  }) async {
    final req = http.MultipartRequest('POST', _u(path));
    req.fields.addAll(fields ?? {});
    if (auth) {
      final headers = await _headers(auth: true);
      final token = headers['Authorization'];
      if (token != null) req.headers['Authorization'] = token;
    }
    if (files != null) {
      for (final f in files) {
        req.files.add(http.MultipartFile.fromBytes(
          f.field,
          f.bytes,
          filename: f.filename,
        ));
      }
    }
    return _requestMultipartWithRetry(req, auth: auth);
  }

  // ---------- 내부 공통 ----------

  static Future<http.Response> _requestWithRetry(
    Future<http.Response> Function() doRequest, {
    required bool auth,
  }) async {
    final first = await doRequest();
    if (!auth || first.statusCode != 401) return first;

    final refreshed = await _refreshAccessToken();
    if (!refreshed) return first;
    return await doRequest();
  }

  static Future<http.StreamedResponse> _requestMultipartWithRetry(
    http.MultipartRequest req, {
    required bool auth,
  }) async {
    http.StreamedResponse first = await req.send();
    if (!auth || first.statusCode != 401) return first;

    final refreshed = await _refreshAccessToken();
    if (!refreshed) return first;

    final headers = await _headers(auth: true);
    final token = headers['Authorization'];
    if (token != null) req.headers['Authorization'] = token;
    return await req.send();
  }

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

/// 외부에서 사용할 수 있게 public으로 변경
class ApiMultipartFile {
  final String field;
  final List<int> bytes;
  final String filename;
  ApiMultipartFile(this.field, this.bytes, this.filename);
}
