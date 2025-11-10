from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=50, blank=True)
    guardian_role = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return self.display_name or getattr(self.user, "username", "user")


# 회원 생성 시 자동으로 Profile 생성/보정
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance: User, created: bool, **kwargs):
    # created 시는 물론, 기존 유저에도 profile이 없으면 보정
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        if not hasattr(instance, "profile"):
            Profile.objects.get_or_create(user=instance)
