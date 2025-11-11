// lib/config.dart
import 'package:flutter/foundation.dart' show kIsWeb, defaultTargetPlatform, TargetPlatform;

class Config {
  /// Base URL 자동 감지:
  /// - Web or Desktop → http://127.0.0.1:8000
  /// - Android Emulator → http://10.0.2.2:8000
  /// - iOS Simulator → http://127.0.0.1:8000
  /// - Physical Device (same Wi-Fi) → http://<PC IP>:8000
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000';
      case TargetPlatform.iOS:
        return 'http://127.0.0.1:8000';
      default:
        return 'http://127.0.0.1:8000';
    }
  }
}
