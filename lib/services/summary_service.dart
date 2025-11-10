
import 'dart:convert';
import 'package:dotori_client/services/api_client.dart';

class SummaryService {
  Future<List<Map<String, dynamic>>> listMySummaries() async {
    final res = await ApiClient.get('/api/summaries/', auth: true);
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      if (data is List) {
        return List<Map<String, dynamic>>.from(data);
      }
    }
    return [];
  }

  Future<bool> createSummary(String text) async {
    final res = await ApiClient.postJson('/api/summaries/create/', {
      'source_text': text,
    }, auth: true);
    return res.statusCode == 201;
  }
}
