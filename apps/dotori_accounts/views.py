# apps/dotori_accounts/views.py
import random

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import signing
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ProfileSerializer,
    PASSWORD_REGEX,
    PHONE_TOKEN_SALT,
    EMAIL_TOKEN_SALT,
)
from .models import Profile, PhoneVerification, EmailVerification, normalize_phone

# 분석 로그 모델 import
from apps.dotori_memberships.models_analytics import UserLoginLog

# 공통 유틸 (CoolSMS)
from apps.dotori_common.utils import send_sms_verification_code

User = get_user_model()

RESEND_COOLDOWN_SEC = 300  # 인증번호 재전송 대기 5분
CODE_LIFETIME_MIN = 5      # 인증번호 유효시간 5분


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            print("[RegisterView] request.data =>", dict(request.data))
        except Exception:
            print("[RegisterView] request.data (print 실패)")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("[RegisterView] errors =>", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        headers = self.get_success_headers({})

        user_data = UserSerializer(user, context={"request": request}).data
        return Response(user_data, status=status.HTTP_201_CREATED, headers=headers)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_object(self):
        return self.request.user


class MyPageProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        prof, _ = Profile.objects.get_or_create(user=self.request.user)
        return prof


# 휴대폰 인증

class SendPhoneCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_phone = request.data.get("phone", "")
        phone = normalize_phone(raw_phone)
        if not phone:
            return Response({"phone": ["전화번호를 입력해주세요."]}, status=400)

        pv = PhoneVerification.objects.filter(phone=phone).first()
        now = timezone.now()
        if pv and (now - pv.last_sent_at).total_seconds() < RESEND_COOLDOWN_SEC:
            remain = RESEND_COOLDOWN_SEC - int((now - pv.last_sent_at).total_seconds())
            return Response(
                {"ok": False, "message": "재전송은 잠시 후에 가능합니다.", "cooldown": max(1, remain)},
                status=429,
            )

        code = f"{random.randint(0, 999999):06d}"
        pv = PhoneVerification.create_or_refresh(phone=phone, code=code, lifetime_min=CODE_LIFETIME_MIN)

        # SMS 발송
        sms_result = send_sms_verification_code(phone, pv.code)

        if not sms_result.ok:
            print(f"[SMS ERROR] {sms_result.message}")
            print(f"[SMS DEBUG] FAILED to send code to {phone}: {pv.code} (expires {pv.expires_at})")
            return Response(
                {"ok": False, "message": "문자 발송에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=500,
            )

        print(f"[SMS DEBUG] Sent code to {phone}: {pv.code} (expires {pv.expires_at})")

        return Response(
            {
                "ok": True,
                "message": "인증번호를 전송했습니다.",
                "cooldown": RESEND_COOLDOWN_SEC,
                "lifetime_sec": CODE_LIFETIME_MIN * 60,
            },
            status=200,
        )


class VerifyPhoneCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_phone = request.data.get("phone", "")
        code = (request.data.get("code") or "").strip()
        phone = normalize_phone(raw_phone)

        if not phone:
            return Response({"phone": ["전화번호를 입력해주세요."]}, status=400)
        if len(code) != 6 or not code.isdigit():
            return Response({"code": ["인증번호 6자리를 정확히 입력해주세요."]}, status=400)

        pv = PhoneVerification.objects.filter(phone=phone).first()
        if not pv:
            return Response({"detail": "인증요청 내역이 없습니다. 먼저 인증번호를 요청해주세요."}, status=400)
        if pv.is_expired():
            return Response({"detail": "인증번호가 만료되었습니다. 다시 요청해주세요."}, status=400)

        pv.attempt_count += 1

        # 인증번호 백도어 허용 로직 추가(개발용 임시)
        if code == "123456":
            pass  
        elif pv.code == code:
            pass  
        else:
            pv.save(update_fields=["attempt_count"])
            return Response({"detail": "인증번호가 올바르지 않습니다."}, status=400)
        #

        pv.verified_at = timezone.now()
        pv.save(update_fields=["verified_at", "attempt_count"])

        token = signing.dumps({"phone": phone, "verified_at": pv.verified_at.isoformat()}, salt=PHONE_TOKEN_SALT)
        return Response({"ok": True, "phone_verified_token": token}, status=200)


# 이메일 인증

class SendEmailCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_email = (request.data.get("email") or "").strip().lower()
        if not raw_email:
            return Response({"email": ["이메일을 입력해주세요."]}, status=400)

        ev = EmailVerification.objects.filter(email=raw_email).first()
        now = timezone.now()
        if ev and (now - ev.last_sent_at).total_seconds() < RESEND_COOLDOWN_SEC:
            remain = RESEND_COOLDOWN_SEC - int((now - ev.last_sent_at).total_seconds())
            return Response(
                {"ok": False, "message": "재전송은 잠시 후에 가능합니다.", "cooldown": max(1, remain)},
                status=429,
            )

        code = f"{random.randint(0, 999999):06d}"
        ev = EmailVerification.create_or_refresh(email=raw_email, code=code, lifetime_min=CODE_LIFETIME_MIN)

        print(f"[EMAIL DEBUG] Send code to {raw_email}: {ev.code} (expires {ev.expires_at})")
        return Response({"OK": True, "cooldown": RESEND_COOLDOWN_SEC, "lifetime_sec": CODE_LIFETIME_MIN * 60}, status=200)


class VerifyEmailCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        if not raw_email:
            return Response({"email": ["이메일을 입력해주세요."]}, status=400)
        if len(code) != 6 or not code.isdigit():
            return Response({"code": ["인증번호 6자리를 정확히 입력해주세요."]}, status=400)

        ev = EmailVerification.objects.filter(email=raw_email).first()
        if not ev:
            return Response({"detail": "인증요청 내역이 없습니다. 먼저 인증번호를 요청해주세요."}, status=400)
        if ev.is_expired():
            return Response({"detail": "인증번호가 만료되었습니다. 다시 요청해주세요."}, status=400)

        ev.attempt_count += 1

        # 개발용 임시(추후 배포시 삭제하거나 관리자용으로 두기.)
        if code == "123456":
            pass  # OK
        elif ev.code == code:
            pass  # OK
        else:
            ev.save(update_fields=["attempt_count"])
            return Response({"detail": "인증번호가 올바르지 않습니다."}, status=400)
        #

        ev.verified_at = timezone.now()
        ev.save(update_fields=["verified_at", "attempt_count"])

        token = signing.dumps({"email": raw_email, "verified_at": ev.verified_at.isoformat()}, salt=EMAIL_TOKEN_SALT)
        return Response({"ok": True, "email_verified_token": token}, status=200)


class ChangeEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        new_email = (request.data.get("new_email") or "").strip().lower()
        token = request.data.get("email_verified_token") or ""

        if not new_email:
            return Response({"new_email": ["새 이메일을 입력해주세요."]}, status=400)
        if new_email == (user.email or "").lower():
            return Response({"new_email": ["현재 이메일과 동일합니다."]}, status=400)

        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response({"new_email": ["이미 사용 중인 이메일입니다."]}, status=400)

        try:
            data = signing.loads(token, salt=EMAIL_TOKEN_SALT, max_age=60 * 5)
        except signing.BadSignature:
            return Response({"email_verified_token": ["이메일 인증 토큰이 올바르지 않습니다."]}, status=400)
        except signing.SignatureExpired:
            return Response({"email_verified_token": ["이메일 인증 토큰이 만료되었습니다. 다시 인증해주세요."]}, status=400)

        if data.get("email") != new_email:
            return Response({"email_verified_token": ["인증된 이메일과 일치하지 않습니다."]}, status=400)

        user.email = new_email
        user.save(update_fields=["email"])
        return Response({"ok": True, "email": new_email}, status=200)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password") or ""
        new_password = request.data.get("new_password") or ""
        new_password_confirm = request.data.get("new_password_confirm") or ""
        phone_token = request.data.get("phone_verified_token") or ""

        if not old_password or not new_password or not new_password_confirm:
            return Response({"detail": "모든 비밀번호 입력란을 채워주세요."}, status=400)

        if not user.check_password(old_password):
            return Response({"old_password": ["현재 비밀번호가 올바르지 않습니다."]}, status=400)

        if new_password != new_password_confirm:
            return Response({"new_password_confirm": ["새 비밀번호가 일치하지 않습니다."]}, status=400)

        if not PASSWORD_REGEX.match(new_password):
            return Response({"new_password": ["비밀번호는 문자와 숫자를 포함해 8자 이상이어야 합니다."]}, status=400)

        try:
            data = signing.loads(phone_token, salt=PHONE_TOKEN_SALT, max_age=60 * 5)
        except signing.BadSignature:
            return Response({"phone_verified_token": ["휴대폰 인증 토큰이 올바르지 않습니다."]}, status=400)
        except signing.SignatureExpired:
            return Response({"phone_verified_token": ["휴대폰 인증 토큰이 만료되었습니다. 다시 인증해주세요."]}, status=400)

        phone_from_token = data.get("phone")
        profile, _ = Profile.objects.get_or_create(user=user)
        if phone_from_token != normalize_phone(profile.phone):
            return Response({"phone_verified_token": ["인증된 휴대폰 번호와 프로필의 번호가 일치하지 않습니다."]}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"ok": True}, status=200)


class UploadProfilePhotoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("image")
        if not file:
            return Response({"detail": "image 파일을 첨부해주세요."}, status=400)

        prof, _ = Profile.objects.get_or_create(user=request.user)
        prof.profile_image = file
        prof.save(update_fields=["profile_image"])

        url = prof.profile_image.url
        if request is not None:
            url = request.build_absolute_uri(url)
        return Response({"ok": True, "profile_image": prof.profile_image.url, "profile_image_url": url}, status=200)


class CheckUsernameView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return Response({"detail": "username is required."}, status=400)

        exists = User.objects.filter(username__iexact=username).exists()
        if exists:
            return Response({"available": False}, status=409)
        return Response({"available": True}, status=200)


class DotoriTokenObtainPairView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            username = (request.data.get("username") or "").strip()
            if username:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = None

                if user:
                    now = timezone.localtime()
                    try:
                        UserLoginLog.objects.create(
                            user=user,
                            hour=now.hour,
                            weekday=now.weekday()
                        )
                    except Exception as e:
                        print(f"[UserLoginLog] create 실패: {e}", flush=True)

        return response
