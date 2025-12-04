# apps/dotori_roleplay/urls.py
from django.urls import path
from .views import RoleplayChatView, RoleplayScenarioListView

app_name = "dotori_roleplay"

urlpatterns = [
    path("chat/", RoleplayChatView.as_view(), name="chat"),
    path("scenarios/", RoleplayScenarioListView.as_view(), name="scenarios"),
]
