# apps/dotori_memberships/views_analytics.py
from datetime import timedelta
from collections import Counter

from django.utils import timezone
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .models_analytics import QuizAttemptLog, RoleplayLog
from apps.dotori_roleplay.scenarios import list_scenarios
from apps.dotori_memberships.models import DailyUsage


class UserAnalyticsView(APIView):
    """
    마이페이지 > 나의 활동 분석

    - 요약 사용 분석 (난이도별)
    - 퀴즈 분석
    - 롤플레잉 분석
    - 이용 패턴 분석
    - 칭찬/리포트 카드
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        now = timezone.now()
        last_30 = today - timedelta(days=30)
        recent_7 = today - timedelta(days=7)

        # -------------------------------------------------
        # 0) 요약 사용 분석: 난이도별
        # -------------------------------------------------
        summary_usage_raw = DailyUsage.objects.filter(
            user=user,
            date__gte=last_30,
            feature_type__in=["SUMMARY_ELEM", "SUMMARY_SECOND", "SUMMARY_ADULT"]
        )

        difficulty_counts = {
            "ELEMENTARY": summary_usage_raw.filter(feature_type="SUMMARY_ELEM")
                            .aggregate(models.Sum("used_count"))["used_count__sum"] or 0,
            "SECONDARY": summary_usage_raw.filter(feature_type="SUMMARY_SECOND")
                            .aggregate(models.Sum("used_count"))["used_count__sum"] or 0,
            "ADULT":     summary_usage_raw.filter(feature_type="SUMMARY_ADULT")
                            .aggregate(models.Sum("used_count"))["used_count__sum"] or 0,
        }

        summary_usage = {
            "enabled": True,
            "difficulty_counts": difficulty_counts,
            "total": (
                difficulty_counts["ELEMENTARY"]
                + difficulty_counts["SECONDARY"]
                + difficulty_counts["ADULT"]
            )
        }

        # -------------------------------------------------
        # 1) 퀴즈/사고력 분석
        # -------------------------------------------------
        quiz_qs = QuizAttemptLog.objects.filter(
            user=user,
            created_at__date__gte=last_30,
        ).order_by("created_at")

        total_quiz = quiz_qs.count()
        correct_total = quiz_qs.filter(is_correct=True).count()

        quiz_7 = quiz_qs.filter(created_at__date__gte=recent_7)
        solved_7 = quiz_7.count()
        correct_7 = quiz_7.filter(is_correct=True).count()

        solved_30 = total_quiz
        correct_30 = correct_total

        quiz_by_day = (
            quiz_qs
            .annotate(day=models.functions.TruncDate("created_at"))
            .values("day")
            .annotate(count=models.Count("id"))
            .order_by("day")
        )
        quiz_daily = [
            {"date": str(row["day"]), "count": row["count"]} for row in quiz_by_day
        ]

        type_accuracy_raw = (
            quiz_qs
            .values("quiz_type")
            .annotate(
                solved=models.Count("id"),
                correct=models.Count("id", filter=models.Q(is_correct=True)),
            )
            .order_by("quiz_type")
        )

        type_accuracy = []
        weakest = None
        weakest_ratio = None

        for row in type_accuracy_raw:
            solved = row["solved"] or 0
            correct = row["correct"] or 0
            ratio = (correct / solved) if solved > 0 else 0.0

            entry = {
                "quiz_type": row["quiz_type"],
                "solved": solved,
                "correct": correct,
                "accuracy": ratio,
            }
            type_accuracy.append(entry)

            if solved > 0:
                if weakest_ratio is None or ratio < weakest_ratio:
                    weakest_ratio = ratio
                    weakest = entry

        # -------------------------------------------------
        # 2) 롤플레잉 분석
        # -------------------------------------------------
        rp_qs = RoleplayLog.objects.filter(
            user=user,
            created_at__date__gte=last_30,
        ).order_by("created_at")

        total_roleplay_turns = rp_qs.count()

        scenario_counter = Counter(rp_qs.values_list("scenario_code", flat=True))
        scenario_meta = {s.code: s for s in list_scenarios()}

        scenario_stats = []
        favorite_scenario = None
        max_count = 0

        for code, cnt in scenario_counter.items():
            s = scenario_meta.get(code)
            title = s.title if s else code
            scenario_stats.append(
                {
                    "scenario_code": code,
                    "title": title,
                    "count": cnt,
                }
            )
            if cnt > max_count:
                max_count = cnt
                favorite_scenario = {
                    "scenario_code": code,
                    "title": title,
                    "count": cnt,
                }

        lengths = list(rp_qs.values_list("user_utterance_len", flat=True))
        avg_len = sum(lengths) / len(lengths) if lengths else 0

        # -------------------------------------------------
        # 3) 이용 패턴 분석
        # -------------------------------------------------
        usage_datetimes = (
            list(quiz_qs.values_list("created_at", flat=True))
            + list(rp_qs.values_list("created_at", flat=True))
        )

        weekday_counter = Counter()
        hour_counter = Counter()

        for dt in usage_datetimes:
            local_dt = timezone.localtime(dt)
            weekday_counter[local_dt.weekday()] += 1
            hour_counter[local_dt.hour] += 1

        weekday_stats = [
            {"weekday": wd, "count": weekday_counter.get(wd, 0)}
            for wd in range(7)
        ]
        hour_stats = [
            {"hour": h, "count": hour_counter.get(h, 0)}
            for h in range(24)
        ]

        best_hour = max(hour_stats, key=lambda x: x["count"]) if usage_datetimes else None
        best_weekday = max(weekday_stats, key=lambda x: x["count"]) if usage_datetimes else None

        if best_hour and best_hour["count"] > 0:
            hour = best_hour["hour"]
            start_block = (hour // 4) * 4
            end_block = start_block + 3
            usage_summary_line = f"당신은 주로 밤 {start_block}~{end_block}시에 앱을 사용해요."
        else:
            usage_summary_line = "아직 충분한 사용 기록이 없습니다."

        # -------------------------------------------------
        # 4) 리포트 카드
        # -------------------------------------------------
        prev_quiz_count = QuizAttemptLog.objects.filter(
            user=user,
            created_at__date__lt=last_30,
        ).count()
        quiz_increase = total_quiz - prev_quiz_count

        prev_roleplay_count = RoleplayLog.objects.filter(
            user=user,
            created_at__date__lt=last_30,
        ).count()
        roleplay_increase = total_roleplay_turns - prev_roleplay_count

        active_dates = set(d.date() for d in usage_datetimes)
        streak_days = len(active_dates)

        report_cards = []

        if total_quiz > 0:
            report_cards.append(
                f"이번 달, 지난달보다 퀴즈를 {max(quiz_increase, 0)}문제 더 풀었어요 👏"
            )

        if total_roleplay_turns > 0:
            if roleplay_increase > 0:
                report_cards.append(
                    f"이번 달, 롤플레잉을 {roleplay_increase}턴 더 연습했어요 👍"
                )
            else:
                report_cards.append("이번 달에도 꾸준히 롤플레잉을 연습하고 있어요 🙂")

        if streak_days >= 3:
            report_cards.append(f"연속 {streak_days}일 이상 활동했어요! 대단해요 🏅")

        # -------------------------------------------------
        # Response JSON
        # -------------------------------------------------
        return Response(
            {
                "summary_usage": summary_usage,  # 🔥 NEW
                "quiz": {
                    "total": total_quiz,
                    "total_solved": total_quiz,
                    "correct_total": correct_total,
                    "solved_7": solved_7,
                    "correct_7": correct_7,
                    "solved_30": solved_30,
                    "correct_30": correct_30,
                    "daily": quiz_daily,
                    "type_accuracy": type_accuracy,
                    "weakest": weakest,
                },
                "roleplay": {
                    "total_turns": total_roleplay_turns,
                    "avg_user_utterance_len": avg_len,
                    "scenario_stats": scenario_stats,
                    "favorite_scenario": favorite_scenario,
                },
                "usage_pattern": {
                    "weekday": weekday_stats,
                    "hour": hour_stats,
                    "summary_line": usage_summary_line,
                },
                "report": {
                    "quiz_increase": quiz_increase,
                    "roleplay_increase": roleplay_increase,
                    "streak_days": streak_days,
                    "cards": report_cards,
                },
            }
        )
