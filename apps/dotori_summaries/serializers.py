from rest_framework import serializers
from .models import Summary
class SummaryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ["id", "source_text"]
class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ["id", "source_text", "result", "status", "created_at", "tts_url"]
