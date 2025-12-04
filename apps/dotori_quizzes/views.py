# apps/dotori_quizzes/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions

from django.contrib.auth import get_user_model

from .selectors import get_next_quiz
from .serializers import (
    QuizPublicSerializer,
    SubmitSerializer,
    SubmitResponseSerializer,
)
from .services import grade_and_record
from .models import Quiz

# ✅ 분석 로그 모델 import
from apps.dotori_memberships.models_analytics import QuizAttemptLog

# ✅ 포인트 적립 서비스 import
from apps.dotori_memberships.services import earn_point_for_quiz_correct

User = get_user_model()


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def next_quiz(request):
    qtype = request.query_params.get("type")
    difficulty = request.query_params.get("difficulty")
    locale = request.query_params.get("locale", "ko")

    quiz = get_next_quiz(qtype, difficulty, locale)
    if not quiz:
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ✅ context에 request를 넘겨서 절대 URL 생성
    data = QuizPublicSerializer(quiz, context={"request": request}).data

    # ✅ 옵션 셔플 시에도 절대 URL 변환 적용
    if hasattr(quiz, "_shuffled_options"):
        opts = []
        for o in quiz._shuffled_options:
            url = getattr(o, "image_url", "") or getattr(
                getattr(o, "image", None), "url", ""
            )
            if url and not str(url).startswith("http"):
                url = request.build_absolute_uri(url)
            opts.append(
                {
                    "id": o.id,
                    "text": o.text,
                    "image_url": url,
                    "alt_text": o.alt_text,
                }
            )
        data["options"] = opts

    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def submit_quiz(request):
    """
    /api/quizzes/submit/

    - grade_and_record 로 정답/점수/연속정답 처리
    - 로그인 유저에 한해:
      1) QuizAttemptLog 에 풀이 기록 저장
      2) 정답일 경우 포인트 적립 (earn_point_for_quiz_correct)
    """
    ser = SubmitSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    payload = ser.validated_data

    user = (
        request.user
        if getattr(request, "user", None) and request.user.is_authenticated
        else None
    )
    user_id = user.id if user is not None else None

    correct, rationale, score_delta, streak = grade_and_record(
        user_id=user_id,
        quiz_id=payload["quiz_id"],
        option_id=payload["option_id"],
        time_ms=payload.get("time_ms", 0),
    )

    # ✅ 퀴즈 풀이 로그 적재 (로그인 유저만)
    try:
        quiz_obj = Quiz.objects.filter(id=payload["quiz_id"]).first()
        if user and quiz_obj:
            QuizAttemptLog.objects.create(
                user=user,
                quiz_id=quiz_obj.id,          # IntegerField
                quiz_type=getattr(quiz_obj, "qtype", ""),
                is_correct=correct,
            )
    except Exception as e:
        print(f"[QuizAttemptLog] create 실패: {e}", flush=True)

    # ✅ 정답일 경우 포인트 적립 (로그인 유저만)
    if user and correct:
        try:
            added = earn_point_for_quiz_correct(user)
            print(f"[POINT] quiz_correct: +{added}P (user={user.id})", flush=True)
        except Exception as e:
            print(f"[POINT] earn_point_for_quiz_correct 실패: {e}", flush=True)

    out = SubmitResponseSerializer(
        {
            "correct": correct,
            "rationale": rationale,
            "score_delta": score_delta,
            "streak": streak,
        }
    ).data
    return Response(out, status=status.HTTP_200_OK)
