import base64
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers


class SummarizeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)

    # Flutter Web 지원용
    image_base64 = serializers.CharField(required=False, allow_blank=True)

    difficulty = serializers.ChoiceField(
        ["ELEMENTARY", "SECONDARY", "ADULT"],
        default="ADULT",
    )

    doc_hint = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
    )

    def validate(self, data):
        text = data.get("text")
        image = data.get("image")
        image_b64 = data.get("image_base64")

    
        # 최소 하나는 필요
    
        if not (text or image or image_b64):
            raise serializers.ValidationError("text 또는 image 중 하나는 필요합니다.")

    
        # base64 → InMemoryUploadedFile 변환
    
        if image_b64 and not image:
            try:
                raw_b64 = image_b64

                # data:image/jpeg;base64,xxxx 제거
                if raw_b64.startswith("data:"):
                    header, raw_b64 = raw_b64.split(",", 1)

                # MIME 타입 추출
                mime = None
                if ";base64" in image_b64 and image_b64.startswith("data:"):
                    mime = image_b64.split(";")[0].replace("data:", "").strip()

                ext = "jpg"
                if mime:
                    if "jpeg" in mime:
                        ext = "jpg"
                    elif "png" in mime:
                        ext = "png"
                    elif "webp" in mime:
                        ext = "webp"

                # base64 decode
                raw = base64.b64decode(raw_b64)

                # 파일 객체 생성
                image_file = InMemoryUploadedFile(
                    BytesIO(raw),
                    field_name="image",
                    name=f"upload.{ext}",
                    content_type=mime or "image/jpeg",
                    size=len(raw),
                    charset=None,
                )

                data["image"] = image_file

            except Exception as e:
                raise serializers.ValidationError(
                    {"image_base64": f"base64 이미지 디코딩 실패: {e}"}
                )

        return data


class ExplainWordSerializer(serializers.Serializer):
    word = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)
