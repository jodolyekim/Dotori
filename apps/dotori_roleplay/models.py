import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class RoleplaySession(models.Model):
    """
    한 번의 역할극 세션(대화방) 단위
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="roleplay_sessions",
    )
    mode = models.CharField(max_length=50, default="daily")      
    locale = models.CharField(max_length=10, default="ko")       
    difficulty = models.CharField(max_length=20, default="EASY") 
    title = models.CharField(max_length=200, blank=True)

    # 모든 대화를 JSON 배열로 저장
    messages = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.user_id}] {self.mode} / {self.difficulty}"
