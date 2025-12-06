# apps/dotori_memberships/services.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    MembershipPlan,
    UserMembership,
    DailyUsage,
    PointWallet,
    PointTransaction,
)
from .exceptions import FeatureLimitExceeded, NotEnoughPoint

# 요금제 코드 상수
BASIC = "BASIC"
PLUS = "PLUS"
PREMIUM = "PREMIUM"


@dataclass
class UsageCheckResult:
  ok: bool
  remaining: int | None  # None = 무제한
  used_today: int


def _get_today() -> date:
  return timezone.localdate()


# 
# 1. 요금제 SEED (BASIC / PLUS / PREMIUM)
# 

_PLANS_INITIALIZED = False


def ensure_plans_seeded() -> None:
  """
  BASIC / PLUS / PREMIUM 요금제가 DB에 없으면 자동 생성.
  여러 번 호출해도 상관 없도록 get_or_create 사용.
  """
  global _PLANS_INITIALIZED
  if _PLANS_INITIALIZED:
    return

  # BASIC (무료)
  MembershipPlan.objects.get_or_create(
    code=BASIC,
    defaults={
      "name": "도토리 BASIC (무료)",
      "description": "일 10회 글요약, 이미지 생성 불가, AI 디텍터 3회",
      "price_monthly": 0,
      "summary_limit_per_day": 10,
      "image_limit_per_day": 0,
      "detector_limit_per_day": 3,
      "point_per_quiz_correct": 1,
      "point_per_roleplay_5min": 1,
      "point_daily_cap": 100,
      "sort_order": 1,
    },
  )

  # PLUS
  MembershipPlan.objects.get_or_create(
    code=PLUS,
    defaults={
      "name": "도토리 PLUS",
      "description": "글요약 무제한, 이미지 3회/일, AI 디텍터 15회/일",
      "price_monthly": 9900,
      "summary_limit_per_day": None,  # 무제한
      "image_limit_per_day": 3,
      "detector_limit_per_day": 15,
      "point_per_quiz_correct": 5,
      "point_per_roleplay_5min": 5,
      "point_daily_cap": 100,
      "sort_order": 2,
    },
  )

  # PREMIUM
  MembershipPlan.objects.get_or_create(
    code=PREMIUM,
    defaults={
      "name": "도토리 PREMIUM",
      "description": "글요약 무제한, 이미지 20회/일, AI 디텍터 50회/일",
      "price_monthly": 14900,
      "summary_limit_per_day": None,  # 무제한
      "image_limit_per_day": 20,
      "detector_limit_per_day": 50,
      "point_per_quiz_correct": 10,
      "point_per_roleplay_5min": 10,
      "point_daily_cap": 100,
      "sort_order": 3,
    },
  )

  _PLANS_INITIALIZED = True


def get_default_plan() -> MembershipPlan:
  """기본 무료 요금제(BASIC) 반환, 없으면 ensure_plans_seeded로 생성"""
  ensure_plans_seeded()
  return MembershipPlan.objects.get(code=BASIC)


# 
# 2. 멤버십 / 지갑 헬퍼
# 


def get_or_create_membership(user) -> UserMembership:
  """
  유저가 처음 들어왔을 때 BASIC 플랜으로 멤버십 생성.
  (views, 다른 서비스에서 사용하는 기본 진입점)
  """
  ensure_plans_seeded()
  membership, _ = UserMembership.objects.get_or_create(
    user=user,
    defaults={"plan": get_default_plan(), "is_active": True},
  )
  # 혹시 plan 이 None 이거나 잘못되어 있으면 BASIC 으로 교정
  if membership.plan is None:
    membership.plan = get_default_plan()
    membership.is_active = True
    membership.save(update_fields=["plan", "is_active"])
  return membership


# 예전 이름과의 호환용 alias (혹시 다른 앱에서 썼을 수도 있어서)
get_or_create_user_membership = get_or_create_membership


def get_user_plan(user) -> MembershipPlan:
  membership = get_or_create_membership(user)
  return membership.plan


def get_wallet(user) -> PointWallet:
  wallet, _ = PointWallet.objects.get_or_create(user=user)
  return wallet


# 예전 이름과의 호환
get_or_create_wallet = get_wallet


# 
# 3. 사용량 한도 체크 / 소비
# 


def _get_limit_from_plan(plan: MembershipPlan, feature_type: str) -> int | None:
  if feature_type == DailyUsage.FEATURE_SUMMARY:
    return plan.summary_limit_per_day
  if feature_type == DailyUsage.FEATURE_IMAGE:
    return plan.image_limit_per_day
  if feature_type == DailyUsage.FEATURE_DETECTOR:
    return plan.detector_limit_per_day
  if feature_type == DailyUsage.FEATURE_POINT_EARN:
    return plan.point_daily_cap
  return None


def check_usage(user, feature_type: str) -> UsageCheckResult:
  """
  단순 조회용: 오늘 사용량과 남은 횟수만 보고 싶을 때 사용.
  """
  plan = get_user_plan(user)
  limit = _get_limit_from_plan(plan, feature_type)
  today = _get_today()

  usage, _ = DailyUsage.objects.get_or_create(
    user=user,
    date=today,
    feature_type=feature_type,
    defaults={"used_count": 0},
  )

  if limit is None:
    # 무제한
    return UsageCheckResult(ok=True, remaining=None, used_today=usage.used_count)

  remaining = max(limit - usage.used_count, 0)
  return UsageCheckResult(
    ok=usage.used_count < limit,
    remaining=remaining,
    used_today=usage.used_count,
  )


@transaction.atomic
def consume_usage(user, feature_type: str, count: int = 1) -> UsageCheckResult:
  """
  기능 사용을 실제로 1회(or count회) 소모.
  한도 초과 시 FeatureLimitExceeded 예외 발생.
  """
  plan = get_user_plan(user)
  limit = _get_limit_from_plan(plan, feature_type)
  today = _get_today()

  usage, _ = DailyUsage.objects.select_for_update().get_or_create(
    user=user,
    date=today,
    feature_type=feature_type,
    defaults={"used_count": 0},
  )

  if limit is None:
    usage.used_count += count
    usage.save(update_fields=["used_count"])
    return UsageCheckResult(ok=True, remaining=None, used_today=usage.used_count)

  if usage.used_count + count > limit:
    remaining = max(limit - usage.used_count, 0)
    raise FeatureLimitExceeded(feature_type, remaining=remaining)

  usage.used_count += count
  usage.save(update_fields=["used_count"])
  remaining = max(limit - usage.used_count, 0)
  return UsageCheckResult(ok=True, remaining=remaining, used_today=usage.used_count)


# 
# 4. 포인트 적립 / 차감
# 


@transaction.atomic
def _earn_points(user, base_point: int, reason: str) -> int:
  """
  실질적인 포인트 적립 로직.
  - 일일 point_daily_cap 을 DailyUsage.FEATURE_POINT_EARN 으로 관리
  """
  if base_point <= 0:
    return 0

  plan = get_user_plan(user)
  cap = plan.point_daily_cap or 0
  today = _get_today()

  usage, _ = DailyUsage.objects.select_for_update().get_or_create(
    user=user,
    date=today,
    feature_type=DailyUsage.FEATURE_POINT_EARN,
    defaults={"used_count": 0},
  )

  if cap <= 0:
    return 0

  remain = max(cap - usage.used_count, 0)
  if remain <= 0:
    return 0

  add_point = min(remain, base_point)

  wallet = get_wallet(user)
  wallet.balance += add_point
  wallet.save(update_fields=["balance"])

  PointTransaction.objects.create(
    user=user,
    tx_type=PointTransaction.TYPE_EARN,
    amount=add_point,
    reason=reason,
    description="Auto earn by rule",
  )

  usage.used_count += add_point
  usage.save(update_fields=["used_count"])

  return add_point


@transaction.atomic
def earn_point_for_quiz_correct(user) -> int:
  """
  사고력 퀴즈 정답 시 포인트 적립.
  """
  plan = get_user_plan(user)
  base_point = plan.point_per_quiz_correct
  return _earn_points(user, base_point, reason=PointTransaction.REASON_QUIZ)


@transaction.atomic
def earn_point_for_roleplay(user, minutes_played: int) -> int:
  """
  상황 역할극 N분 진행 시 포인트 적립 (5분 단위).
  """
  if minutes_played < 5:
    return 0
  units = minutes_played // 5
  plan = get_user_plan(user)
  base_point = plan.point_per_roleplay_5min * units
  return _earn_points(user, base_point, reason=PointTransaction.REASON_ROLEPLAY)


@transaction.atomic
def spend_points(user, amount: int, reason: str, description: str = "") -> None:
  """
  포인트 사용 (이용권 결제 시 차감).
  """
  if amount <= 0:
    return

  wallet = get_wallet(user)
  if wallet.balance < amount:
    raise NotEnoughPoint(needed=amount, current=wallet.balance)

  wallet.balance -= amount
  wallet.save(update_fields=["balance"])

  PointTransaction.objects.create(
    user=user,
    tx_type=PointTransaction.TYPE_SPEND,
    amount=amount,
    reason=reason,
    description=description,
  )


# views.py 에서 쓰는 이름과 맞추기 위한 alias
def spend_point(user, amount: int, reason: str, description: str = "") -> None:
  return spend_points(user, amount, reason, description)
