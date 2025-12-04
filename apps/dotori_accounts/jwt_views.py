# apps/dotori_accounts/jwt_views.py
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.response import Response
from rest_framework import status

# ✅ 로그인 로그 모델
from apps.dotori_memberships.models_analytics import UserLoginLog

User = get_user_model()


class DotoriTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/token/
    - 기본 JWT 발급 + 로그인 성공 시 UserLoginLog 적재
    """

    def post(self, request, *args, **kwargs):
        # 원래 SimpleJWT 동작 그대로 수행
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        # 토큰 응답 생성
        data = serializer.validated_data
        response = Response(data, status=status.HTTP_200_OK)

        # ✅ 로그인 성공 시 접속 로그 남기기
        try:
            username = (request.data.get("username") or "").strip()
            password = request.data.get("password") or ""

            user = authenticate(request=request, username=username, password=password)
            if user is not None:
                now = timezone.localtime()
                UserLoginLog.objects.create(
                    user=user,
                    user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:255],
                    ip_address=request.META.get("REMOTE_ADDR", ""),
                    weekday=now.weekday(),  # 0=월요일 ~ 6=일요일
                    hour=now.hour,          # 0~23시
                )
        except Exception as e:
            # 로그인 로그 적재 실패해도 JWT 발급은 그대로
            print(f"[DotoriTokenObtainPairView] UserLoginLog 저장 실패: {e}", flush=True)

        return response
