from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SummaryJob(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    source_type = models.CharField(max_length=10, choices=[('text','text'),('file','file'),('image','image')])
    options = models.JSONField(default=dict, blank=True)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
