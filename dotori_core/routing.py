from django.urls import re_path
from apps.dotori_quizzes.consumers import QuizConsumer

websocket_urlpatterns = [
    re_path(r"ws/quiz/(?P<room_name>\w+)/$", QuizConsumer.as_asgi()),
]
