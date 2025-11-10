
# Dotori Flutter Client

## Quick Start
```bash
# 1) Make an empty Flutter project here (to generate android/ios/web folders)
flutter create .

# 2) Replace the generated `lib/` and `pubspec.yaml` with these files (already in this zip)
flutter pub get

# 3) Update the base URL in `lib/config.dart` (default http://10.0.2.2:8000 for Android emulator)
#    For iOS simulator, you can use http://localhost:8000
#    For physical device, use your machine IP (e.g., http://192.168.x.x:8000)

# 4) Run
flutter run
```

### Backend endpoints used
- POST /api/auth/register/
- POST /api/auth/token/
- GET  /api/auth/me/
- GET  /api/summaries/
- POST /api/summaries/create/
