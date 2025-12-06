# dotori_core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic import TemplateView

#  JWT 로그인 관련 
from apps.dotori_accounts.jwt_views import DotoriTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

#  요약 API (이미지 생성 기능 제거됨) 
from apps.dotori_summaries.views import SummarizeAPI


def ping(request):
    return JsonResponse({"status": "ok", "app": "dotori", "version": "dev"})


urlpatterns = [
    path("admin/", admin.site.urls),

    #  앱별 API 
    path("api/auth/", include("apps.dotori_accounts.urls")),
    path("api/documents/", include("apps.dotori_documents.urls")),
    path("api/summaries/", include("apps.dotori_summaries.urls")),
    path("api/quizzes/", include("apps.dotori_quizzes.urls")),
    path("api/roleplay/", include("apps.dotori_roleplay.urls")),
    path("api/detector/", include("apps.dotori_detector.urls")),
    path("api/memberships/", include("apps.dotori_memberships.urls")),

    #  JWT 
    path("api/auth/token/", DotoriTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    #  요약 (호환용 단일 엔드포인트) 
    path("api/summarize/", SummarizeAPI.as_view()),

    #  ComicAPI 완전 삭제됨
    # path("api/comic/", ComicAPI.as_view()),

    #  홈/헬스체크 
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("ping/", ping),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
