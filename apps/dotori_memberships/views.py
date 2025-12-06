# apps/dotori_memberships/views.py
from django.db import transaction
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MembershipPlan,
    UserMembership,
    PaymentTransaction,
    PointTransaction,
    DailyUsage,
)
from .serializers import (
    MembershipPlanSerializer,
    UserMembershipSerializer,
    PointWalletSerializer,
    PointTransactionSerializer,
)
from .services import (
    get_or_create_membership,
    get_wallet,
    spend_point,
)
from .exceptions import NotEnoughPoint


class IsAuth(permissions.IsAuthenticated):
    """권한 체크 alias"""
    pass


=
#   요금제 목록 조회
=
class MembershipPlanListView(generics.ListAPIView):
    permission_classes = [IsAuth]
    serializer_class = MembershipPlanSerializer

    def get_queryset(self):
        return MembershipPlan.objects.filter(is_active=True).order_by(
            "sort_order", "id"
        )


=
#   내 멤버십 조회
=
class MyMembershipView(APIView):
    permission_classes = [IsAuth]

    def get(self, request):
        membership = get_or_create_membership(request.user)
        return Response(UserMembershipSerializer(membership).data)


=
#   포인트 잔액 조회
=
class PointSummaryView(APIView):
    permission_classes = [IsAuth]

    def get(self, request):
        wallet = get_wallet(request.user)
        return Response(PointWalletSerializer(wallet).data)


=
#   포인트 사용/적립 내역 조회
=
class PointHistoryView(generics.ListAPIView):
    permission_classes = [IsAuth]
    serializer_class = PointTransactionSerializer

    def get_queryset(self):
        return (
            PointTransaction.objects.filter(user=self.request.user)
            .order_by("-created_at")
        )


=
#   멤버십 결제 (가짜 PG)
=
class SubscribeMembershipView(APIView):
    """
    멤버십 구독 / 변경 API

    요청 형식:
    {
        "plan_code": "PLUS",
        "payment_method": "CARD",
        "point_to_use": 3000
    }

    응답:
    - 결제결과
    - 변경된 내 멤버십 정보
    - 포인트 잔액
    """

    permission_classes = [IsAuth]

    def post(self, request):
        user = request.user

        plan_code = request.data.get("plan_code")
        payment_method = request.data.get("payment_method", "CARD")
        point_to_use = int(request.data.get("point_to_use") or 0)

        if not plan_code:
            return Response({"detail": "plan_code is required"}, status=400)

        #  요금제 조회 
        try:
            plan = MembershipPlan.objects.get(code=plan_code, is_active=True)
        except MembershipPlan.DoesNotExist:
            return Response({"detail": "Invalid plan_code"}, status=400)

        amount_total = max(plan.price_monthly, 0)

        #  포인트 사용 
        if point_to_use < 0:
            point_to_use = 0
        if point_to_use > amount_total:
            point_to_use = amount_total

        if point_to_use > 0:
            try:
                spend_point(
                    user,
                    amount=point_to_use,
                    reason=PointTransaction.REASON_PURCHASE_DISCOUNT,
                    description=f"Membership {plan.code} discount",
                )
            except NotEnoughPoint as e:
                return Response({"detail": str(e)}, status=400)

        amount_paid_cash = amount_total - point_to_use

        #  결제 내역 생성 (PG 없음 → 즉시 성공) 
        payment = PaymentTransaction.objects.create(
            user=user,
            plan=plan,
            amount_total=amount_total,
            amount_point_used=point_to_use,
            amount_paid_cash=amount_paid_cash,
            payment_method=payment_method,
            status=PaymentTransaction.STATUS_SUCCESS,
        )

        #  멤버십 업데이트 
        membership = get_or_create_membership(user)
        membership.plan = plan
        membership.is_active = True
        membership.save()

        wallet = get_wallet(user)

        return Response(
            {
                "payment_id": payment.id,
                "payment_status": payment.status,
                "amount_total": amount_total,
                "amount_point_used": point_to_use,
                "amount_paid_cash": amount_paid_cash,
                "membership": UserMembershipSerializer(membership).data,
                "wallet": PointWalletSerializer(wallet).data,
            },
            status=200,
        )



#   사용량 통계(overview)
#   /api/memberships/stats/overview/

class MembershipUsageOverviewView(APIView):
    """
    오늘 기준 사용량 + 포인트 요약

    응답 예시:
    {
      "summary":  {"limit": 10, "used": 3, "remaining": 7},
      "image":    {"limit": 0,  "used": 0, "remaining": 0},
      "detector": {"limit": 3,  "used": 1, "remaining": 2},
      "points":   {"balance": 1500, "today_earned": 20, "daily_cap": 100}
    }
    """

    permission_classes = [IsAuth]

    def get(self, request):
        user = request.user
        membership = get_or_create_membership(user)
        plan = membership.plan
        today = timezone.localdate()

        def _build_feature(feature_type: str, limit_value: int | None):
            usage = DailyUsage.objects.filter(
                user=user,
                date=today,
                feature_type=feature_type,
            ).first()
            used = usage.used_count if usage else 0
            if limit_value is None:
                remaining = None
            else:
                remaining = max(limit_value - used, 0)
            return {
                "limit": limit_value,
                "used": used,
                "remaining": remaining,
            }

        summary_stat = _build_feature(
            DailyUsage.FEATURE_SUMMARY, plan.summary_limit_per_day
        )
        image_stat = _build_feature(
            DailyUsage.FEATURE_IMAGE, plan.image_limit_per_day
        )
        detector_stat = _build_feature(
            DailyUsage.FEATURE_DETECTOR, plan.detector_limit_per_day
        )

        wallet = get_wallet(user)
        point_usage = DailyUsage.objects.filter(
            user=user,
            date=today,
            feature_type=DailyUsage.FEATURE_POINT_EARN,
        ).first()
        today_earned = point_usage.used_count if point_usage else 0

        return Response(
            {
                "summary": summary_stat,
                "image": image_stat,
                "detector": detector_stat,
                "points": {
                    "balance": wallet.balance,
                    "today_earned": today_earned,
                    "daily_cap": plan.point_daily_cap,
                },
            }
        )


#   기능 사용 consume API
#   /api/memberships/consume/<feature_type>/

class FeatureConsumeView(APIView):
    """
    SUMMARY / IMAGE / DETECTOR 기능 사용 1회 소모

    요청: POST /api/memberships/consume/SUMMARY/
    응답:
    {
      "ok": true,
      "limit": 10,
      "used_today": 3,
      "remaining": 7
    }
    """

    permission_classes = [IsAuth]

    VALID_FEATURES = {
        "SUMMARY": DailyUsage.FEATURE_SUMMARY,
        "IMAGE": DailyUsage.FEATURE_IMAGE,
        "DETECTOR": DailyUsage.FEATURE_DETECTOR,
    }

    def post(self, request, feature_type: str):
        user = request.user
        ft = self.VALID_FEATURES.get(feature_type.upper())
        if not ft:
            return Response({"detail": "Invalid feature_type"}, status=400)

        membership = get_or_create_membership(user)
        plan = membership.plan
        today = timezone.localdate()

        # plan에서 한도 가져오기
        if ft == DailyUsage.FEATURE_SUMMARY:
            limit = plan.summary_limit_per_day
        elif ft == DailyUsage.FEATURE_IMAGE:
            limit = plan.image_limit_per_day
        elif ft == DailyUsage.FEATURE_DETECTOR:
            limit = plan.detector_limit_per_day
        else:
            limit = None

        with transaction.atomic():
            usage, _ = DailyUsage.objects.select_for_update().get_or_create(
                user=user,
                date=today,
                feature_type=ft,
                defaults={"used_count": 0},
            )

            # 무제한이면 그냥 증가만
            if limit is not None and usage.used_count >= limit:
                remaining = max(limit - usage.used_count, 0)
                return Response(
                    {
                        "ok": False,
                        "limit": limit,
                        "used_today": usage.used_count,
                        "remaining": remaining,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            usage.used_count += 1
            usage.save(update_fields=["used_count"])

        remaining = None if limit is None else max(limit - usage.used_count, 0)

        return Response(
            {
                "ok": True,
                "limit": limit,
                "used_today": usage.used_count,
                "remaining": remaining,
            }
        )
