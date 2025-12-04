from django.urls import path
from .views import DetectTextView, DetectImageView, DetectAudioView, DetectVideoView

urlpatterns = [
    path("text/",  DetectTextView.as_view(),  name="detect_text"),
    path("image/", DetectImageView.as_view(), name="detect_image"),
    path("audio/", DetectAudioView.as_view(), name="detect_audio"),
    path("video/", DetectVideoView.as_view(), name="detect_video"),  # ✅ 신규
]
