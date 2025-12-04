# apps/dotori_roleplay/serializers.py
from rest_framework import serializers


class RoleplayStartSerializer(serializers.Serializer):
    """
    역할극 세션을 새로 시작할 때 사용하는 입력 폼
    예)
    {
      "mode": "daily",
      "locale": "ko",
      "difficulty": "EASY",
      "topic": "카페에서 음료 주문하기"
    }
    """
    mode = serializers.CharField(required=False, default="daily")
    locale = serializers.CharField(required=False, default="ko")
    difficulty = serializers.CharField(required=False, default="EASY")
    topic = serializers.CharField(required=False, allow_blank=True)


class RoleplayReplySerializer(serializers.Serializer):
    """
    기존 세션에 대해 유저 발화를 이어붙일 때 사용
    예)
    {
      "session_id": "UUID...",
      "user_message": "2번으로 할게요."
    }
    """
    session_id = serializers.UUIDField()
    user_message = serializers.CharField()
