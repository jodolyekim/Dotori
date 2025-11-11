from rest_framework import serializers
from .models import Document
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "original_name", "file", "uploaded_at", "text_cache"]
        read_only_fields = ["id", "uploaded_at", "text_cache"]
