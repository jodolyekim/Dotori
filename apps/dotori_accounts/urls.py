# apps/dotori_accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    MeView,
    MyPageProfileView,
    SendPhoneCodeView,
    VerifyPhoneCodeView,
    SendEmailCodeView,
    VerifyEmailCodeView,
    ChangeEmailView,
    ChangePasswordView,
    UploadProfilePhotoView,
    CheckUsernameView,
    DotoriTokenObtainPairView,   # ✅ 커스텀 JWT 로그인 뷰
)

urlpatterns = [
    # 회원가입/내 정보
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/", MyPageProfileView.as_view(), name="mypage_profile"),
    path("profile/upload_photo/", UploadProfilePhotoView.as_view(), name="profile_upload_photo"),

    # JWT (로그인 + 갱신)
    path("token/", DotoriTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 휴대폰 인증
    path("phone/send_code/", SendPhoneCodeView.as_view(), name="phone_send_code"),
    path("phone/verify_code/", VerifyPhoneCodeView.as_view(), name="phone_verify_code"),

    # 이메일 인증 + 변경
    path("email/send_code/", SendEmailCodeView.as_view(), name="email_send_code"),
    path("email/verify_code/", VerifyEmailCodeView.as_view(), name="email_verify_code"),
    path("email/change/", ChangeEmailView.as_view(), name="email_change"),

    # 비밀번호 변경
    path("password/change/", ChangePasswordView.as_view(), name="password_change"),

    # 아이디 중복확인
    path("check-username/", CheckUsernameView.as_view(), name="check_username"),
]
