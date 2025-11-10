from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

User = get_user_model()


def normalize_phone(phone: str) -> str:
    """숫자만 남기고 표준화 (예: '010-1234-5678' -> '01012345678')"""
    return "".join(ch for ch in (phone or "") if ch.isdigit())


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=50, blank=True)
    guardian_role = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)  # 선택: 전화번호 보관

    def __str__(self) -> str:
        return self.display_name or getattr(self.user, "username", "user")


# 휴대폰 인증 관리
class PhoneVerification(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_verified(self) -> bool:
        return self.verified_at is not None

    @classmethod
    def create_or_refresh(cls, phone: str, code: str, lifetime_min: int = 30) -> "PhoneVerification":
        now = timezone.now()
        pv, _ = cls.objects.update_or_create(
            phone=normalize_phone(phone),
            defaults={
                "code": code,
                "expires_at": now + timezone.timedelta(minutes=lifetime_min),
                "last_sent_at": now,
                "attempt_count": 0,
            },
        )
        return pv


# 회원 생성 시 프로필 자동 생성/보정
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance: User, created: bool, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        if not hasattr(instance, "profile"):
            Profile.objects.get_or_create(user=instance)
