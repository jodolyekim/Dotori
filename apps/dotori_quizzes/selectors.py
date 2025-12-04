# apps/dotori_quizzes/selectors.py
from __future__ import annotations
import random
from django.db.models import Prefetch
from .models import Quiz, Option

__all__ = ["get_next_quiz"]

def get_next_quiz(qtype: str | None, difficulty: str | None, locale: str = "ko") -> Quiz | None:
    """
    조건(타입/난이도/로케일)으로 퀴즈 하나를 랜덤 선택.
    보기(Option)는 서버에서 셔플하여 quiz._shuffled_options 로 담아둠.
    """
    qs = Quiz.objects.filter(locale=locale)
    if qtype:
        qs = qs.filter(qtype=qtype)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    qs = qs.prefetch_related(Prefetch("options", queryset=Option.objects.all()))
    quiz = qs.order_by("?").first()
    if not quiz:
        return None

    opts = list(quiz.options.all())
    random.shuffle(opts)
    # 셔플 결과를 임시 속성에 저장(Serializer에서 사용)
    quiz._shuffled_options = opts
    return quiz
