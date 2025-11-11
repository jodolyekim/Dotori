# dotori_core/urls.py  ← 이 파일이 실제로 쓰입니다 (settings: dotori_core.settings)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic import TemplateView

# 호환용 단일 엔드포인트를 위해 직접 view import
from apps.dotori_summaries.views import SummarizeAPI, ComicAPI

def ping(request):
    return JsonResponse({"status": "ok", "app": "dotori", "version": "dev"})

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---- 앱별 API (정규 경로) ----
    path("api/auth/", include("apps.dotori_accounts.urls")),
    path("api/documents/", include("apps.dotori_documents.urls")),
    path("api/summaries/", include("apps.dotori_summaries.urls")),
    path("api/quizzes/", include("apps.dotori_quizzes.urls")),

    # ---- 호환 경로(클라이언트가 /api/summarize/ /api/comic/ 를 호출해도 되게) ----
    path("api/summarize/", SummarizeAPI.as_view()),
    path("api/comic/",     ComicAPI.as_view()),

    # ---- 홈 & 헬스체크 ----
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("ping/", ping, name="ping"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
