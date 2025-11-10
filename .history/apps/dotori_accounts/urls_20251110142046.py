from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView

urlpatterns = [
    # 회원가입
    path("register/", RegisterView.as_view(), name="register"),

    # JWT 토큰 발급 / 갱신
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 내 정보 조회
    path("me/", MeView.as_view(), name="me"),
]
