# apps/dotori_memberships/models.py
from django.conf import settings
from django.db import models


class MembershipPlan(models.Model):
    """요금제(멤버십) 정의 테이블"""
    code = models.CharField(max_length=32, unique=True)  # BASIC / PLUS / PREMIUM
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    price_monthly = models.PositiveIntegerField(help_text="월 정기결제 금액 (KRW)")

    # 사용 한도 (None = 무제한)
    summary_limit_per_day = models.PositiveIntegerField(null=True, blank=True)
    image_limit_per_day = models.PositiveIntegerField(null=True, blank=True)
    detector_limit_per_day = models.PositiveIntegerField(null=True, blank=True)

    # 포인트 관련
    point_per_quiz_correct = models.PositiveIntegerField(default=0)
    point_per_roleplay_5min = models.PositiveIntegerField(default=0)
    point_daily_cap = models.PositiveIntegerField(default=100)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class UserMembership(models.Model):
    """사용자별 현재 멤버십 (1:1)"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name="user_memberships",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.user} -> {self.plan.code}"


class DailyUsage(models.Model):
    """일단위 기능 사용량 기록"""
    FEATURE_SUMMARY = "SUMMARY"
    FEATURE_IMAGE = "IMAGE"
    FEATURE_DETECTOR = "DETECTOR"
    FEATURE_POINT_EARN = "POINT_EARN"

    FEATURE_CHOICES = [
        (FEATURE_SUMMARY, "Summary"),
        (FEATURE_IMAGE, "Image Generation"),
        (FEATURE_DETECTOR, "AI Detector"),
        (FEATURE_POINT_EARN, "Point Earn"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_usages",
    )
    date = models.DateField()
    feature_type = models.CharField(max_length=16, choices=FEATURE_CHOICES)
    used_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date", "feature_type")

    def __str__(self) -> str:
        return f"{self.user} {self.date} {self.feature_type}={self.used_count}"


class PointWallet(models.Model):
    """포인트 잔액"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_wallet",
    )
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} balance={self.balance}"


class PointTransaction(models.Model):
    """포인트 적립/사용 내역"""
    TYPE_EARN = "EARN"
    TYPE_SPEND = "SPEND"

    TX_TYPE_CHOICES = [
        (TYPE_EARN, "Earn"),
        (TYPE_SPEND, "Spend"),
    ]

    REASON_QUIZ = "QUIZ_CORRECT"
    REASON_ROLEPLAY = "ROLEPLAY"
    REASON_PURCHASE_DISCOUNT = "PURCHASE_DISCOUNT"
    REASON_ADJUST = "ADJUST"

    REASON_CHOICES = [
        (REASON_QUIZ, "Quiz correct"),
        (REASON_ROLEPLAY, "Roleplay"),
        (REASON_PURCHASE_DISCOUNT, "Purchase discount"),
        (REASON_ADJUST, "Manual adjust"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    tx_type = models.CharField(max_length=8, choices=TX_TYPE_CHOICES)
    amount = models.PositiveIntegerField()
    reason = models.CharField(max_length=32, choices=REASON_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def signed_amount(self):
        return self.amount if self.tx_type == self.TYPE_EARN else -self.amount


class PaymentTransaction(models.Model):
    """결제 로그"""
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"

    METHOD_CARD = "CARD"
    METHOD_EASY = "EASY_PAY"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT)

    amount_total = models.PositiveIntegerField()
    amount_point_used = models.PositiveIntegerField(default=0)
    amount_paid_cash = models.PositiveIntegerField(default=0)

    payment_method = models.CharField(max_length=32, default=METHOD_CARD)
    status = models.CharField(max_length=32, default=STATUS_SUCCESS)

    created_at = models.DateTimeField(auto_now_add=True)


# 🔥 분석 전용 모델들(SummaryDetailLog, QuizAttemptLog, UserLoginLog, RoleplayLog 등)
#    models_analytics.py 에 정의되어 있고, 여기서 import 해서
#    Django가 "이 앱의 모델"로 인식하게 만든다.
from .models_analytics import *  # noqa
