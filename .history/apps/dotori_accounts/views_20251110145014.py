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
RESEND_COOLDOWN_SEC = 60      # 재전송 쿨다운
CODE_LIFETIME_MIN = 30        # 인증번호 유효시간(분)


class RegisterView(generics.CreateAPIView):
    """
    최종 회원가입
    - POST /api/auth/register/
    - body:
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


class MeView(generics.RetrieveAPIView):
    """
    내 정보 조회 (JWT 필요)
    - GET /api/auth/me/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ---- 휴대폰 인증 흐름 --------------------------------------------------------

class SendPhoneCodeView(APIView):
    """
    인증번호 발송
    - POST /api/auth/phone/send_code/
      { "phone": "01012345678" }
    - resp: { "ok": true, "cooldown": 60 }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_phone = request.data.get("phone", "")
        phone = normalize_phone(raw_phone)
        if not phone:
            return Response({"phone": ["전화번호를 입력해주세요."]}, status=400)

        # 쿨다운 체크
        pv = PhoneVerification.objects.filter(phone=phone).first()
        now = timezone.now()
        if pv and (now - pv.last_sent_at).total_seconds() < RESEND_COOLDOWN_SEC:
            remain = RESEND_COOLDOWN_SEC - int((now - pv.last_sent_at).total_seconds())
            return Response(
                {"ok": False, "message": "재전송은 잠시 후에 가능합니다.", "cooldown": max(1, remain)},
                status=429,
            )

        # 6자리 난수 생성
        code = f"{random.randint(0, 999999):06d}"
        pv = PhoneVerification.create_or_refresh(phone=phone, code=code, lifetime_min=CODE_LIFETIME_MIN)

        # TODO: 실제 SMS 연동 (NCP SENS/토스트/카카오/티윌리오 등)
        # 여기서는 개발 편의상 콘솔에만 출력
        print(f"[SMS DEBUG] Send code to {phone}: {pv.code} (expires {pv.expires_at})")

        return Response({"ok": True, "cooldown": RESEND_COOLDOWN_SEC}, status=200)


class VerifyPhoneCodeView(APIView):
    """
    인증번호 검증
    - POST /api/auth/phone/verify_code/
      { "phone": "01012345678", "code": "123456" }
    - resp: { "ok": true, "phone_verified_token": "<signed>" }
    """
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

        # 성공
        pv.verified_at = timezone.now()
        pv.save(update_fields=["verified_at", "attempt_count"])

        token = signing.dumps({"phone": phone, "verified_at": pv.verified_at.isoformat()}, salt=PHONE_TOKEN_SALT)
        return Response({"ok": True, "phone_verified_token": token}, status=200)
