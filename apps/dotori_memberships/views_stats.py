# apps/dotori_memberships/view_stats.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .models import (
    DailyUsage,
    PointTransaction,
)
from .services import (
    get_or_create_membership,
    get_wallet,
)


class IsAuth(permissions.IsAuthenticated):
    """JWT 인증 유저만 접근"""
    pass


class MembershipStatsOverview(APIView):
    """
    마이페이지 분석용 통합 정보
    GET /api/memberships/stats/overview/

    ⚠️ Flutter `MembershipOverviewScreen`에서 기대하는 포맷에 맞춰 반환:
    {
      "membership": {...},
      "summary":   { "limit": ..., "used": ..., "remaining": ..., "dates": [...], "last_7_days": [...] },
      "image":     { ... },
      "detector":  { ... },
      "points":    {
        "balance": ...,
        "today_earned": ...,
        "daily_cap": ...,
        "last_7_days": [...]
      },

      # (하위 호환용 – 혹시 모를 다른 곳에서 쓸 수도 있으니 유지)
      "usage_today": {...},
      "usage_last_7_days": {...},
    }
    """
    permission_classes = [IsAuth]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        #  멤버십 정보 
        membership = get_or_create_membership(user)
        plan = membership.plan  # MembershipPlan 인스턴스

        #  오늘 사용량 조회 
        def get_usage(feature):
            usage = DailyUsage.objects.filter(
                user=user,
                date=today,
                feature_type=feature
            ).first()
            return usage.used_count if usage else 0

        summary_used = get_usage(DailyUsage.FEATURE_SUMMARY)
        detector_used = get_usage(DailyUsage.FEATURE_DETECTOR)
        image_used = get_usage(DailyUsage.FEATURE_IMAGE)

        # 요금제 한도
        summary_limit = plan.summary_limit_per_day
        detector_limit = plan.detector_limit_per_day
        image_limit = plan.image_limit_per_day

        # 남은 횟수 계산 (None = 무제한 → remaining = -1 로 내려줘서 프론트에서 '무제한' 처리 가능)
        def calc_remaining(limit, used):
            if limit is None:
                return -1
            return max(limit - used, 0)

        summary_remaining = calc_remaining(summary_limit, summary_used)
        detector_remaining = calc_remaining(detector_limit, detector_used)
        image_remaining = calc_remaining(image_limit, image_used)

        #  최근 7일 데이터 
        dates = []
        summary_list = []
        detector_list = []
        image_list = []
        point_list = []

        for i in range(7):
            day = today - timedelta(days=6 - i)
            dates.append(str(day))

            # Summary
            s = DailyUsage.objects.filter(
                user=user,
                date=day,
                feature_type=DailyUsage.FEATURE_SUMMARY
            ).first()
            summary_list.append(s.used_count if s else 0)

            # Detector
            d = DailyUsage.objects.filter(
                user=user,
                date=day,
                feature_type=DailyUsage.FEATURE_DETECTOR
            ).first()
            detector_list.append(d.used_count if d else 0)

            # Image
            im = DailyUsage.objects.filter(
                user=user,
                date=day,
                feature_type=DailyUsage.FEATURE_IMAGE
            ).first()
            image_list.append(im.used_count if im else 0)

            # Points earned (당일 적립 합계)
            pt = PointTransaction.objects.filter(
                user=user,
                tx_type=PointTransaction.TYPE_EARN,
                created_at__date=day
            )
            point_list.append(sum(p.amount for p in pt))

        #  포인트 정보 
        wallet = get_wallet(user)

        today_point_tx = PointTransaction.objects.filter(
            user=user,
            tx_type=PointTransaction.TYPE_EARN,
            created_at__date=today,
        )
        today_earned = sum(t.amount for t in today_point_tx)

        # 요금제에 설정된 일일 포인트 상한
        daily_cap = plan.point_daily_cap or 0

        #  최종 응답 
        return Response({
            #  멤버십 요약 
            "membership": {
                "plan_code": plan.code,
                "plan_name": plan.name,
                "expires_at": membership.expires_at,
            },

            #  (하위 호환용) 오늘 사용량 원본 
            "usage_today": {
                "summary_used": summary_used,
                "summary_limit": summary_limit,
                "detector_used": detector_used,
                "detector_limit": detector_limit,
                "image_used": image_used,
                "image_limit": image_limit,
            },

            #  (하위 호환용) 최근 7일 원본 
            "usage_last_7_days": {
                "dates": dates,
                "summary": summary_list,
                "detector": detector_list,
                "image": image_list,
            },

            #  Flutter MembershipOverviewScreen 이 직접 쓰는 형식 
            "summary": {
                "limit": summary_limit,
                "used": summary_used,
                "remaining": summary_remaining,
                "dates": dates,
                "last_7_days": summary_list,
            },
            "image": {
                "limit": image_limit,
                "used": image_used,
                "remaining": image_remaining,
                "dates": dates,
                "last_7_days": image_list,
            },
            "detector": {
                "limit": detector_limit,
                "used": detector_used,
                "remaining": detector_remaining,
                "dates": dates,
                "last_7_days": detector_list,
            },
            "points": {
                "balance": wallet.balance,
                "today_earned": today_earned,
                "daily_cap": daily_cap,
                "last_7_days": point_list,
            },
        })
