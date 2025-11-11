from rest_framework import serializers

class SummarizeRequestSerializer(serializers.Serializer):
    text   = serializers.CharField(required=False, allow_blank=True)
    image  = serializers.ImageField(required=False)
    style  = serializers.ChoiceField(['bulleted','paragraph','minutes'], default='bulleted')
    length = serializers.ChoiceField(['one_line','short','medium','long'], default='short')

    def validate(self, data):
        # ✅ 파일 업로드 제거: text 또는 image만 허용
        if not any([data.get('text'), data.get('image')]):
            raise serializers.ValidationError("text 또는 image 중 하나는 필요합니다.")
        return data

class ComicRequestSerializer(serializers.Serializer):
    summary = serializers.CharField()
