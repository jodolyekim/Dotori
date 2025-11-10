from django.contrib.auth import get_user_model
from rest_framework import serializers, validators
from .models import Profile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(
        max_length=150,
        validators=[
            validators.UniqueValidator(
                queryset=User.objects.all(),
                message="이미 사용 중인 아이디입니다.",
            )
        ],
    )
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        email = validated_data.get("email") or ""
        user = User.objects.create_user(
            username=validated_data["username"],
            email=email,
            password=validated_data["password"],
        )
        # 회원가입 시 프로필 자동 생성 (에러가 나더라도 회원가입은 진행되도록 보호)
        try:
            Profile.objects.get_or_create(user=user)
        except Exception:
            pass
        return user
