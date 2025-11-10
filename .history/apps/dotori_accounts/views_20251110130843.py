from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """
    회원가입 엔드포인트
    - POST /api/auth/register/
    - body: { "username": "...", "password": "...", "email": "..." (선택) }
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    """
    내 정보 조회 (JWT 필요)
    - GET /api/auth/me/
    - Header: Authorization: Bearer <access>
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
