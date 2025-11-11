import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:dotori_client/services/auth_service.dart';

// 삭제: file_picker
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:dotori_client/services/api_client.dart';
import '../config.dart'; // ✅ Base URL 인식용

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // 기존 /me 테스트
  String? _meText;
  String? _error;
  bool _loading = false;

  // 요약/이미지 상태
  final _textCtrl = TextEditingController();
  String? _summary;
  List<String> _images = [];
  bool _loadingSummary = false;
  bool _loadingImages = false;

  // ---------------- 기존 /api/auth/me ----------------
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
    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(context, '/', (_) => false);
  }

  // ---------------- 요약/만화 변환 ----------------
  Future<void> _summarizeFromText() async {
    final text = _textCtrl.text.trim();
    if (text.isEmpty) {
      _snack('텍스트를 입력하세요.');
      return;
    }
    setState(() {
      _loadingSummary = true;
      _summary = null;
      _images = [];
    });
    try {
      final res = await ApiClient.postJson('/api/summarize/', {
        'text': text,
        'style': 'bulleted',
        'length': 'short',
      });
      if (res.statusCode != 200) throw Exception(res.body);
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      setState(() => _summary = data['summary'] as String);
    } catch (e) {
      _snack('요약 실패: $e');
    } finally {
      setState(() => _loadingSummary = false);
    }
  }

  // 🔥 파일 업로드 흐름 제거됨

  Future<void> _summarizeFromImage() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (x == null) return;
    final Uint8List bytes = await x.readAsBytes();

    setState(() {
      _loadingSummary = true;
      _summary = null;
      _images = [];
    });
    try {
      final streamed = await ApiClient.postMultipart(
        '/api/summarize/',
        fields: {'style': 'bulleted', 'length': 'short'},
        files: [ApiMultipartFile('image', bytes, 'image.jpg')],
      );
      final res = await http.Response.fromStream(streamed);
      if (res.statusCode != 200) throw Exception(res.body);
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      setState(() => _summary = data['summary'] as String);
    } catch (e) {
      _snack('요약 실패: $e');
    } finally {
      setState(() => _loadingSummary = false);
    }
  }

  Future<void> _toComic() async {
    if (_summary == null) {
      _snack('먼저 요약을 생성하세요.');
      return;
    }
    setState(() {
      _loadingImages = true;
      _images = [];
    });
    try {
      final res =
          await ApiClient.postJson('/api/comic/', {'summary': _summary!});
      if (res.statusCode != 200) throw Exception(res.body);
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final imgs = List<String>.from(data['images'] ?? []);
      print('🧩 [BACKEND RESPONSE] images=$imgs');
      setState(() => _images = imgs);
    } catch (e, st) {
      print('❌ [TO COMIC ERROR] $e\n$st');
      _snack('이미지 변환 실패: $e');
    } finally {
      setState(() => _loadingImages = false);
    }
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  /// ✅ 절대경로 변환 + 디버깅 로그 포함 이미지 위젯
  Widget _buildNetworkImage(String src) {
    if (src.isEmpty) return Container(color: Colors.grey.shade200);

    final resolvedSrc =
        src.startsWith('http') ? src : '${Config.baseUrl}$src';
    print('🖼️ [IMAGE BUILD] src=$src → resolved=$resolvedSrc');

    return Image.network(
      resolvedSrc,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) {
        print('❌ [IMAGE ERROR] failed to load $resolvedSrc');
        return Container(
          color: Colors.grey.shade300,
          child: const Icon(Icons.error_outline),
        );
      },
      loadingBuilder: (_, child, progress) {
        if (progress == null) return child;
        return const Center(child: CircularProgressIndicator(strokeWidth: 2));
      },
    );
  }

  // ---------------- UI ----------------
  @override
  Widget build(BuildContext context) {
    final dense = const EdgeInsets.symmetric(vertical: 10);
    final theme = Theme.of(context);

    print('🧠 [STATE] summary=${_summary != null}, images=${_images.length}');

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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child:
            Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          // /me 테스트
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
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.black12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(_meText!,
                  style: const TextStyle(fontFamily: 'monospace')),
            ),
          if (_error != null)
            Text(_error!, style: const TextStyle(color: Colors.red)),
          const Divider(height: 32),

          // 글 요약 & 만화 변환 (같은 페이지)
          Text('글 요약 & 만화 변환', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _textCtrl,
            maxLines: 6,
            decoration: const InputDecoration(
              hintText: '텍스트를 붙여넣거나 아래에서 사진을 선택하세요',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            ElevatedButton(
              onPressed: _loadingSummary ? null : _summarizeFromText,
              child: _loadingSummary
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('요약하기(텍스트)'),
            ),
            // 🔥 파일 업로드 버튼 제거됨
            OutlinedButton(
              onPressed: _loadingSummary ? null : _summarizeFromImage,
              child: const Text('사진 첨부(OCR)'),
            ),
          ]),
          const SizedBox(height: 12),
          if (_summary != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.black12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(_summary!),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _loadingImages ? null : _toComic,
              child: _loadingImages
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('이미지로 변환(같은 페이지)'),
            ),
          ],
          const SizedBox(height: 12),
          if (_images.isNotEmpty)
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
              ),
              itemCount: _images.length,
              itemBuilder: (_, i) => ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: _buildNetworkImage(_images[i]), // ✅ 절대경로 처리 적용
              ),
            ),
        ]),
      ),
    );
  }
}
