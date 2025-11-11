from django.db import models
class Quiz(models.Model):
    title = models.CharField(max_length=120)
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
class QuizResult(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    score = models.IntegerField(default=0)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
