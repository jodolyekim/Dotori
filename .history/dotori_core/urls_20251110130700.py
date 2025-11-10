from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # ✅ 추가

def ping(request):
    return JsonResponse({"status": "ok", "app": "dotori", "version": "dev"})

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ 로그인 관련 (JWT 토큰 발급/갱신)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ✅ 앱별 API
    path("api/auth/", include("apps.dotori_accounts.urls")),
    path("api/documents/", include("apps.dotori_documents.urls")),
    path("api/summaries/", include("apps.dotori_summaries.urls")),
    path("api/quizzes/", include("apps.dotori_quizzes.urls")),

    # 홈 페이지 & 헬스체크
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("ping/", ping, name="ping"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
