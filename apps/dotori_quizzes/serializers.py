from rest_framework import serializers
from .models import Quiz, Option


# 
# 절대 URL 변환 유틸
# 
def _abs_url(request, url: str | None) -> str:
    """상대 URL을 절대 URL로 변환"""
    if not url:
        return ""
    if str(url).startswith("http"):
        return url
    return request.build_absolute_uri(url) if request else url


# 
# 보기 (Option)
# 
class OptionPublicSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get("request")
        # image_url 필드 또는 ImageField(url) 모두 처리
        url = getattr(obj, "image_url", "") or getattr(getattr(obj, "image", None), "url", "")
        return _abs_url(request, url)

    class Meta:
        model = Option
        fields = ("id", "text", "image_url", "alt_text")


# 
# 퀴즈 (Quiz)
# 
class QuizPublicSerializer(serializers.ModelSerializer):
    options = OptionPublicSerializer(many=True)
    prompt_img = serializers.SerializerMethodField()

    def get_prompt_img(self, obj):
        request = self.context.get("request")
        url = getattr(obj, "prompt_img", "") or getattr(getattr(obj, "prompt_image", None), "url", "")
        return _abs_url(request, url)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "qtype",
            "difficulty",
            "locale",
            "prompt_text",
            "prompt_img",
            "hint_text",
            "options",
        )


# 
# 정답 제출용 Serializer
# 
class SubmitSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    option_id = serializers.IntegerField()
    time_ms = serializers.IntegerField(required=False, default=0)


class SubmitResponseSerializer(serializers.Serializer):
    correct = serializers.BooleanField()
    rationale = serializers.CharField(allow_blank=True)
    score_delta = serializers.IntegerField()
    streak = serializers.IntegerField()
