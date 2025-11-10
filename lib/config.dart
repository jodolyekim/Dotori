import 'dart:io';
import 'package:flutter/foundation.dart';

class Config {
  /// Base URL 자동 감지:
  /// - Web or Desktop → http://127.0.0.1:8000
  /// - Android Emulator → http://10.0.2.2:8000
  /// - Physical Device (same Wi-Fi) → http://<PC IP>:8000
  static String get baseUrl {
    // 웹(Chrome 등)
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }

    // 모바일 플랫폼만 검사 가능
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    if (Platform.isIOS) {
      // iOS 시뮬레이터에서는 localhost로 접근 가능
      return 'http://127.0.0.1:8000';
    }

    // 데스크톱 (Windows/macOS/Linux)
    return 'http://127.0.0.1:8000';
  }
}
