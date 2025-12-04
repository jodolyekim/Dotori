from django.urls import path
from .views import SummarizeAPI, ExplainWordAPI

app_name = "dotori_summaries"

urlpatterns = [
    # /api/summaries/summarize/
    path("summarize/", SummarizeAPI.as_view(), name="summarize"),

    # /api/summaries/word-explain/
    path("word-explain/", ExplainWordAPI.as_view(), name="word-explain"),
]
