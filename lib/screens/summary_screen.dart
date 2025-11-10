
import 'package:flutter/material.dart';
import 'package:dotori_client/services/summary_service.dart';

class SummaryScreen extends StatefulWidget {
  const SummaryScreen({super.key});
  @override
  State<SummaryScreen> createState() => _SummaryScreenState();
}

class _SummaryScreenState extends State<SummaryScreen> {
  final _svc = SummaryService();
  final _text = TextEditingController();
  bool _loading = false;
  List<Map<String, dynamic>> items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    items = await _svc.listMySummaries();
    if (mounted) setState(() {});
  }

  Future<void> _create() async {
    setState(() => _loading = true);
    final ok = await _svc.createSummary(_text.text);
    await _load();
    setState(() => _loading = false);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? '요약 요청 완료' : '요약 요청 실패')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('요약 만들기')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _text,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: '원문 텍스트',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _create,
                child: _loading ? const SizedBox(width:16,height:16,child:CircularProgressIndicator(strokeWidth:2)) : const Text('요약 생성'),
              ),
            ),
            const Divider(height: 32),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: ListView.separated(
                  itemBuilder: (_, i) {
                    final it = items[i];
                    return ListTile(
                      title: Text(it['result'] ?? '(처리 중)'),
                      subtitle: Text(it['source_text'] ?? ''),
                      trailing: Text(it['status'] ?? ''),
                    );
                  },
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemCount: items.length,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
