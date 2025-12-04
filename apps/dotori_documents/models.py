from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
class Document(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="docs/")
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    text_cache = models.TextField(blank=True)
    def __str__(self):
        return self.original_name or self.file.name
