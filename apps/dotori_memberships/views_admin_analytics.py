from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import models

from .models import DailyUsage, MembershipPlan, UserMembership, PaymentTransaction
from .models_analytics import QuizAttemptLog, SummaryDetailLog, UserLoginLog


User = get_user_model()


class AdminAnalyticsView(APIView):
    """운영자 대시보드 분석"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        today = timezone.localdate()
        last_30 = today - timedelta(days=30)

        # 1) 활성 사용자수 ----------------------------
        dau = UserLoginLog.objects.filter(created_at__date=today).count()
        wau = (
            UserLoginLog.objects.filter(created_at__date__gte=today - timedelta(days=7))
            .values("user")
            .distinct()
            .count()
        )
        mau = (
            UserLoginLog.objects.filter(created_at__date__gte=last_30)
            .values("user")
            .distinct()
            .count()
        )

        # 2) 기능 사용량 ------------------------------
        summary_count = DailyUsage.objects.filter(
            feature_type="SUMMARY",
            date__gte=last_30
        ).aggregate(total=models.Sum("used_count"))["total"] or 0

        detector_count = DailyUsage.objects.filter(
            feature_type="DETECTOR",
            date__gte=last_30
        ).aggregate(total=models.Sum("used_count"))["total"] or 0

        quiz_count = QuizAttemptLog.objects.filter(
            created_at__date__gte=last_30
        ).count()

        # 3) 멤버십 분석 ------------------------------
        plan_stats = (
            UserMembership.objects.values("plan__code")
            .annotate(count=models.Count("id"))
        )

        payments = PaymentTransaction.objects.filter(
            created_at__date__gte=last_30
        )
        revenue = payments.aggregate(total=models.Sum("amount_paid_cash"))["total"] or 0

        return Response({
            "active_users": {
                "dau": dau, "wau": wau, "mau": mau
            },
            "usage": {
                "summary": summary_count,
                "detector": detector_count,
                "quiz": quiz_count,
            },
            "membership": {
                "plans": list(plan_stats),
                "revenue_30days": revenue,
            }
        })
