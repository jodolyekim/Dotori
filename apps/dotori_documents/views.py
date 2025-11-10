from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.uploadedfile import UploadedFile
from .models import Document
from .serializers import DocumentSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).order_by("-uploaded_at")
    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user)
        f: UploadedFile = obj.file
        if getattr(f, "content_type", None) in ["text/plain","application/json"] or f.name.endswith(".txt"):
            try:
                obj.text_cache = f.read().decode("utf-8", errors="ignore")
                obj.save()
            except Exception:
                pass
    @action(detail=True, methods=["post"])
    def extract_text(self, request, pk=None):
        doc = self.get_object()
        return Response({"ok": True, "text": doc.text_cache})
