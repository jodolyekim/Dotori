import random
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import signing
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, UserSerializer
from .models import PhoneVerification, normalize_phone

User = get_user_model()

PHONE_TOKEN_SALT = "dotori_phone_verified"
RESEND_COOLDOWN_SEC = 60
CODE_LIFETIME_MIN = 30


class RegisterView(generics.CreateAPIView):
    """
    최종 회원가입
    - POST /api/auth/register/
    body:
      {
        "username": "...",
        "email": "...",
        "password": "...",   # 문자+숫자 8자 이상
        "name": "...",
        "phone": "01012345678",
        "phone_verified_token": "<signed>"
      }
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    # ✅ 콘솔에 요청/에러를 찍어서 정확한 원인을 즉시 확인
    def create(self, request, *args, **kwargs):
        try:
            print("[RegisterView] request.data =>", dict(request.data))
        except Exception:
            print("[RegisterView] request.data (print 실패)")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("[RegisterView] errors =>", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


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

        print(f"[SMS DEBUG] Send code to {phone}: {pv.code} (expires {pv.expires_at})")
        return Response({"ok": True, "cooldown": RESEND_COOLDOWN_SEC}, status=200)


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
        if pv.code != code:
            pv.save(update_fields=["attempt_count"])
            return Response({"detail": "인증번호가 올바르지 않습니다."}, status=400)

        pv.verified_at = timezone.now()
        pv.save(update_fields=["verified_at", "attempt_count"])

        token = signing.dumps({"phone": phone, "verified_at": pv.verified_at.isoformat()}, salt=PHONE_TOKEN_SALT)
        return Response({"ok": True, "phone_verified_token": token}, status=200)


# ✅ 아이디 중복확인
class CheckUsernameView(APIView):
    """
    GET /api/auth/check-username/?username=foo
    - 사용 가능: 200 {"available": true}
    - 중복:     409 {"available": false}
    - 파라미터 없음: 400
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return Response({"detail": "username is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 필요 시 형식 검증 추가 가능 (예: 영문/숫자/_ 3~30자)
        # import re
        # if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        #     return Response({"detail": "invalid username format."},
        #                     status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        exists = User.objects.filter(username__iexact=username).exists()
        if exists:
            return Response({"available": False}, status=status.HTTP_409_CONFLICT)
        return Response({"available": True}, status=status.HTTP_200_OK)
