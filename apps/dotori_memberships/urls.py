# apps/dotori_memberships/urls.py
from django.urls import path

from .views import (
    MembershipPlanListView,
    MyMembershipView,
    PointSummaryView,
    PointHistoryView,
    SubscribeMembershipView,
    MembershipUsageOverviewView,
    FeatureConsumeView,
)

# 🔥 분석 기능 import (새 파일)
from .views_analytics import UserAnalyticsView
from .views_admin_analytics import AdminAnalyticsView

app_name = "dotori_memberships"

urlpatterns = [
    path("plans/", MembershipPlanListView.as_view(), name="plan-list"),
    path("me/", MyMembershipView.as_view(), name="my-membership"),
    path("points/", PointSummaryView.as_view(), name="point-summary"),
    path("points/history/", PointHistoryView.as_view(), name="point-history"),
    path("subscribe/", SubscribeMembershipView.as_view(), name="subscribe-membership"),

    # 기존 사용량 분석(멤버십 사용량)
    path(
        "stats/overview/",
        MembershipUsageOverviewView.as_view(),
        name="stats-overview",
    ),
    path(
        "consume/<str:feature_type>/",
        FeatureConsumeView.as_view(),
        name="consume-feature",
    ),

    # ============================
    #   🔥 새로 추가된 "분석 기능"
    # ============================

    # 1) 사용자 개인 분석 데이터(API)
    path(
        "analytics/user/",
        UserAnalyticsView.as_view(),
        name="user-analytics",
    ),

    # 2) 관리자 대시보드 분석(API)
    path(
        "analytics/admin/",
        AdminAnalyticsView.as_view(),
        name="admin-analytics",
    ),
]
