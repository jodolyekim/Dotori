// lib/services/summary_service.dart
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:dotori_client/services/api_client.dart';

const String kBackendBase = "http://127.0.0.1:8000";

class ComicResult {
  final List<String> images;
  final List<String>? captions;
  final String? size;
  final String? provider;

  ComicResult({
    required this.images,
    this.captions,
    this.size,
    this.provider,
  });
}

class SummaryService {
  String _abs(String url) =>
      url.startsWith('http') ? url : '$kBackendBase${url.startsWith('/') ? '' : '/'}$url';

  List<String> _normalizeAndAbs(List<dynamic>? raw) {
    if (raw == null) return [];
    return raw
        .map((e) => (e?.toString() ?? ''))
        .map((s) => s.replaceAll('\n', '').trim())
        .where((s) => s.isNotEmpty)
        .map(_abs)
        .toList();
  }

  // 🧠 텍스트 → 요약
  Future<String> summarizeFromText(
    String text, {
    String style = 'bulleted',
    String length = 'short',
  }) async {
    final res = await ApiClient.postJson(
      '/api/summarize/',
      {'text': text, 'style': style, 'length': length},
      auth: false,
    );
    if (res.statusCode != 200) {
      throw Exception('요약 실패: ${res.statusCode} ${res.body}');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return data['summary'] as String;
  }

  // 🖼️ 이미지(OCR) → 요약 (파일경로 버전)
  Future<String> summarizeFromImage(
    String filePath, {
    String style = 'bulleted',
    String length = 'short',
  }) async {
    final bytes = await File(filePath).readAsBytes();
    return summarizeFromImageBytes(bytes, style: style, length: length);
  }

  // 🖼️ 이미지(OCR) → 요약 (바이트 버전)
  Future<String> summarizeFromImageBytes(
    Uint8List bytes, {
    String style = 'bulleted',
    String length = 'short',
  }) async {
    final streamed = await ApiClient.postMultipart(
      '/api/summarize/',
      fields: {'style': style, 'length': length},
      files: [ApiMultipartFile('image', bytes, 'image.jpg')],
      auth: false,
    );
    final res = await http.Response.fromStream(streamed);
    if (res.statusCode != 200) {
      throw Exception('요약 실패: ${res.statusCode} ${res.body}');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return data['summary'] as String;
  }

  // ✅ 요약문 → 4컷 이미지 (상세 응답)
  Future<ComicResult> comicFromSummaryDetailed(String summary) async {
    final res = await ApiClient.postJson(
      '/api/comic/',
      {'summary': summary},
      auth: false,
    );
    if (res.statusCode != 200) {
      throw Exception('이미지 변환 실패: ${res.statusCode} ${res.body}');
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;

    final images = _normalizeAndAbs(data['images'] as List?);
    final captions = (data['captions'] is List)
        ? (data['captions'] as List)
            .map((e) => (e?.toString() ?? '').trim())
            .where((s) => s.isNotEmpty)
            .toList()
        : null;

    final size = data['size']?.toString();
    final provider = data['provider']?.toString();

    return ComicResult(
      images: images,
      captions: captions,
      size: size,
      provider: provider,
    );
  }

  // 🧩 구버전 호환: 이미지 배열만 받기
  Future<List<String>> comicFromSummary(String summary) async {
    final res = await ApiClient.postJson(
      '/api/comic/',
      {'summary': summary},
      auth: false,
    );
    if (res.statusCode != 200) {
      throw Exception('이미지 변환 실패: ${res.statusCode} ${res.body}');
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return _normalizeAndAbs(data['images'] as List?);
  }
}
