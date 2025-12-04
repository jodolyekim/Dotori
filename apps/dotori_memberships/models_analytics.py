# apps/dotori_memberships/models_analytics.py
from django.conf import settings
from django.db import models


class SummaryDetailLog(models.Model):
    """요약 상세 기록 (사용자 요약 분석용 - 지금은 사용 안 해도 됨)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    text_length = models.PositiveIntegerField(default=0)
    summary_type = models.CharField(max_length=20, default="text")  # "text" / "comic" / "ocr" 등
    category = models.CharField(max_length=30, blank=True, default="")  # 연애 / 학교 / 일상 …

    def __str__(self):
        return f"{self.user} - {self.summary_type} ({self.created_at.date()})"


class QuizAttemptLog(models.Model):
    """퀴즈 풀이 기록"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz_id = models.IntegerField()               # quiz PK 저장
    quiz_type = models.CharField(max_length=30)   # 감정이해 / 상황판단 / 대화예절 …
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} quiz={self.quiz_id} correct={self.is_correct}"


class UserLoginLog(models.Model):
    """
    접속 패턴 분석용 — 앱 열 때마다 기록
    (지금은 사용 패턴을 퀴즈/롤플레이에서 직접 뽑을 거라 필수는 아님,
     나중에 원하면 이걸로 로그인 패턴만 따로 볼 수도 있음.)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    hour = models.PositiveIntegerField(default=0)    # 0~23
    weekday = models.PositiveIntegerField(default=0) # 0=월, 6=일

    def __str__(self):
        return f"{self.user} login at {self.created_at}"


class RoleplayLog(models.Model):
    """
    롤플레잉 대화 기록 (분석용)
    - 한 번의 /api/roleplay/chat/ 호출을 '1턴'으로 보고 저장
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    scenario_code = models.CharField(max_length=50)   # 어떤 시나리오인지 (예: FRIEND_FALL_DOWN)
    user_utterance_len = models.PositiveIntegerField(default=0)  # 사용자가 마지막에 한 발화 길이(문자 수)

    def __str__(self):
        return f"{self.user} scenario={self.scenario_code} at {self.created_at}"
