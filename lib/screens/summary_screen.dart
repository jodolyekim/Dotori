// lib/screens/summary_screen.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/summary_service.dart';
import '../config.dart';

class SummaryScreen extends StatefulWidget {
  const SummaryScreen({super.key});

  @override
  State<SummaryScreen> createState() => _SummaryScreenState();
}

class _SummaryScreenState extends State<SummaryScreen> {
  final _svc = SummaryService();
  final _textCtrl = TextEditingController();

  String? _summary;
  List<String> _images = [];
  List<String> _captions = [];
  String? _size;
  bool _loadingSummary = false;
  bool _loadingImages = false;

  // 🧠 텍스트 요약
  Future<void> _summarizeFromText() async {
    final text = _textCtrl.text.trim();
    if (text.isEmpty) return;
    setState(() => _loadingSummary = true);
    try {
      final s = await _svc.summarizeFromText(text, style: 'bulleted', length: 'short');
      setState(() {
        _summary = s;
        _images = [];
        _captions = [];
        _size = null;
      });
    } finally {
      if (mounted) setState(() => _loadingSummary = false);
    }
  }

  // 🖼️ 이미지(OCR)
  Future<void> _summarizeFromImage() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (x == null) return;
    setState(() => _loadingSummary = true);
    try {
      final s = await _svc.summarizeFromImage(x.path);
      setState(() {
        _summary = s;
        _images = [];
        _captions = [];
        _size = null;
      });
    } finally {
      if (mounted) setState(() => _loadingSummary = false);
    }
  }

  // 🎨 요약 → 만화 이미지
  Future<void> _toComic() async {
    if (_summary == null) return;
    setState(() => _loadingImages = true);
    try {
      final res = await _svc.comicFromSummaryDetailed(_summary!);
      print("🧩 [BACKEND RESPONSE] images=${res.images}");
      print("🧩 [BACKEND RESPONSE] captions=${res.captions}");
      print("🧩 [BACKEND RESPONSE] size=${res.size}");
      print("🧩 [BACKEND RESPONSE] provider=${res.provider}");

      setState(() {
        _images = res.images;
        _captions = res.captions ?? List.generate(res.images.length, (i) => '');
        _size = res.size;
      });
    } catch (err, st) {
      print("❌ [toComic ERROR] $err\n$st");
      final imgs = await _svc.comicFromSummary(_summary!);
      print("🧩 [BACKEND FALLBACK] images=$imgs");
      setState(() {
        _images = imgs;
        _captions = List.generate(imgs.length, (i) => '');
        _size = null;
      });
    } finally {
      if (mounted) setState(() => _loadingImages = false);
    }
  }

  /// ✅ 이미지 표시 (URL 전용, /media → 절대경로 변환)
  Widget _buildImage(String src) {
    if (src.isEmpty) return Container(color: Colors.grey.shade200);

    final resolvedSrc = src.startsWith('http') ? src : '${Config.baseUrl}$src';
    print('🖼️ [IMAGE BUILD] src=$src → resolved=$resolvedSrc');

    return Image.network(
      resolvedSrc,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) {
        print("❌ [IMAGE ERROR] failed to load $resolvedSrc");
        return Container(
          color: Colors.grey.shade300,
          child: const Icon(Icons.error_outline),
        );
      },
      loadingBuilder: (_, child, progress) {
        if (progress == null) return child;
        print("⏳ [IMAGE LOADING] $resolvedSrc (${progress.cumulativeBytesLoaded ?? 0} bytes)");
        return const Center(child: CircularProgressIndicator(strokeWidth: 2));
      },
    );
  }

  Widget _comicTile(String src, String caption) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: AspectRatio(
        aspectRatio: 1,
        child: Stack(
          fit: StackFit.expand,
          children: [
            _buildImage(src),
            if (caption.isNotEmpty)
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  color: Colors.black.withOpacity(0.5),
                  child: Text(
                    caption,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 12, height: 1.2),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final ButtonStyle primaryBtn = ElevatedButton.styleFrom(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    );

    final validImages = _images.where((s) => s.isNotEmpty).toList();

    print("🧠 [STATE] summary=${_summary != null}, images=${_images.length}, validImages=${validImages.length}");

    return Scaffold(
      appBar: AppBar(title: const Text('글 요약 & 만화 변환')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _textCtrl,
              maxLines: 6,
              decoration: const InputDecoration(
                hintText: '텍스트를 붙여넣거나 아래에서 사진을 선택하세요',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton(
                  onPressed: _loadingSummary ? null : _summarizeFromText,
                  style: primaryBtn,
                  child: _loadingSummary
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('요약하기(텍스트)'),
                ),
                // ✅ 파일 업로드 버튼 제거됨
                OutlinedButton(
                  onPressed: _loadingSummary ? null : _summarizeFromImage,
                  child: const Text('사진 첨부(OCR)'),
                ),
              ],
            ),
            const Divider(height: 32),
            if (_summary != null) ...[
              Text('요약 결과', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
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
                style: primaryBtn,
                child: _loadingImages
                    ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('이미지로 변환'),
              ),
              if (_size != null) ...[
                const SizedBox(height: 8),
                Text('이미지 생성 사이즈: $_size', style: theme.textTheme.bodySmall),
              ],
              const SizedBox(height: 12),
            ],
            if (validImages.isNotEmpty)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 1,
                ),
                itemCount: validImages.length,
                itemBuilder: (_, i) {
                  final cap = i < _captions.length ? _captions[i] : '';
                  return _comicTile(validImages[i], cap);
                },
              ),
          ],
        ),
      ),
    );
  }
}
