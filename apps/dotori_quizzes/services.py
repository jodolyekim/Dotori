# apps/dotori_quizzes/services.py
from __future__ import annotations
from .models import Quiz, Option, SessionResult

def grade_and_record(user_id: int | None, quiz_id: int, option_id: int, time_ms: int = 0):
    """
    - 정답 여부 판정
    - 간단 점수 계산(정답 +10)
    - 세션 기록 저장
    - 최근 기록 기준 streak 계산
    반환: (correct, rationale, score_delta, streak)
    """
    quiz = Quiz.objects.get(id=quiz_id)
    chosen = Option.objects.get(id=option_id, quiz=quiz)

    correct = bool(chosen.is_correct)
    score_delta = 10 if correct else 0

    # streak 계산: 최근 기록에서 연속 정답 길이
    qs = SessionResult.objects.filter(user_id=user_id).order_by("-id")
    streak = 0
    for r in qs[:10]:
        if r.correct:
            streak += 1
        else:
            break
    if correct:
        streak += 1  # 이번 정답을 반영

    SessionResult.objects.create(
        user_id=user_id,
        quiz=quiz,
        chosen_opt=chosen,
        correct=correct,
        time_ms=time_ms or 0,
    )

    rationale = chosen.rationale or ""
    return correct, rationale, score_delta, streak
