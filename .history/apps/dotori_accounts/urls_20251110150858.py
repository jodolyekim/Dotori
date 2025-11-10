from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, MeView,
    SendPhoneCodeView, VerifyPhoneCodeView,
    CheckUsernameView,  # ← 추가
)

urlpatterns = [
    # 회원가입/내 정보
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),

    # JWT
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 휴대폰 인증
    path("phone/send_code/", SendPhoneCodeView.as_view(), name="phone_send_code"),
    path("phone/verify_code/", VerifyPhoneCodeView.as_view(), name="phone_verify_code"),

    # ✅ 아이디 중복확인
    path("check-username/", CheckUsernameView.as_view(), name="check_username"),
]
