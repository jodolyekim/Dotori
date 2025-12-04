# apps/dotori_quizzes/urls.py
from django.urls import path
from .views import next_quiz, submit_quiz

urlpatterns = [
    path("next", next_quiz),
    path("submit", submit_quiz),
]
