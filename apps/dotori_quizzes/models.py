from django.db import models

class QuizType(models.TextChoices):
    SENTENCE_MEANING = "SENTENCE_MEANING", "문장 의미"
    SITUATION_TEXT   = "SITUATION_TEXT", "상황-텍스트"
    SITUATION_IMAGE  = "SITUATION_IMAGE", "상황-이미지"

class Difficulty(models.TextChoices):
    EASY   = "EASY", "하"
    MEDIUM = "MEDIUM", "중"
    HARD   = "HARD", "상"

class Quiz(models.Model):
    qtype       = models.CharField(max_length=32, choices=QuizType.choices)
    locale      = models.CharField(max_length=10, default="ko")
    difficulty  = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.EASY)
    prompt_text = models.TextField(blank=True)
    prompt_img  = models.URLField(blank=True)
    # 접근성/타깃(경계선 지능 사용자 고려)
    hint_text   = models.CharField(max_length=255, blank=True)  # 짧은 힌트
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["qtype", "difficulty", "locale"]),
        ]

class Option(models.Model):
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="options")
    text        = models.CharField(max_length=512, blank=True)
    image_url   = models.URLField(blank=True)
    alt_text    = models.CharField(max_length=256, blank=True)
    is_correct  = models.BooleanField(default=False)
    rationale   = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

class SessionResult(models.Model):
    user_id     = models.IntegerField(null=True, blank=True)  # 익명 허용
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    chosen_opt  = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True)
    correct     = models.BooleanField(default=False)
    time_ms     = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
