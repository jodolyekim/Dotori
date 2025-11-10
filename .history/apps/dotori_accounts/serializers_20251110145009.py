import re
from django.contrib.auth import get_user_model
from rest_framework import serializers, validators
from django.core import signing
from django.utils import timezone

from .models import Profile, PhoneVerification, normalize_phone

User = get_user_model()

PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")  # 문자+숫자 포함 8자 이상
PHONE_TOKEN_SALT = "dotori_phone_verified"


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "display_name", "phone")

    def get_display_name(self, obj):
        return getattr(getattr(obj, "profile", None), "display_name", "")

    def get_phone(self, obj):
        return getattr(getattr(obj, "profile", None), "phone", "")


class RegisterSerializer(serializers.ModelSerializer):
    # 추가 필드
    name = serializers.CharField(required=True, max_length=50)
    phone = serializers.CharField(required=True, max_length=20)
    phone_verified_token = serializers.CharField(write_only=True)
    # 기존 필드
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(
        max_length=150,
        validators=[
            validators.UniqueValidator(
                queryset=User.objects.all(),
                message="이미 사용 중인 아이디입니다.",
            )
        ],
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "name", "phone", "phone_verified_token")

    def validate_password(self, value):
        if not PASSWORD_REGEX.match(value or ""):
            raise serializers.ValidationError("비밀번호는 문자와 숫자를 포함해 8자 이상이어야 합니다.")
        return value

    def validate(self, attrs):
        # phone_verified_token 검증 (30분 유효)
        token = attrs.get("phone_verified_token")
        phone = normalize_phone(attrs.get("phone"))
        try:
            data = signing.loads(token, salt=PHONE_TOKEN_SALT, max_age=60 * 30)
        except signing.BadSignature:
            raise serializers.ValidationError({"phone_verified_token": "휴대폰 인증 토큰이 올바르지 않습니다."})
        except signing.SignatureExpired:
            raise serializers.ValidationError({"phone_verified_token": "휴대폰 인증 토큰이 만료되었습니다. 다시 인증해주세요."})

        if data.get("phone") != phone:
            raise serializers.ValidationError({"phone_verified_token": "인증된 휴대폰 번호와 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        username = validated_data["username"]
        password = validated_data["password"]
        name = validated_data["name"]
        phone = normalize_phone(validated_data["phone"])

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        # 프로필 업데이트
        prof, _ = Profile.objects.get_or_create(user=user)
        prof.display_name = name
        prof.phone = phone
        prof.save()
        return user
