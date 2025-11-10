from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
class Summary(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="summaries")
    source_text = models.TextField()
    result = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="PENDING")
    tts_url = models.URLField(blank=True)
    def __str__(self): return f"Summary {self.id} ({self.status})"
