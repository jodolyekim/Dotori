# apps/dotori_summaries/urls.py
from django.urls import path
from .views import SummarizeAPI, ComicAPI

app_name = "dotori_summaries"

urlpatterns = [
    # /api/summaries/summarize/
    path("summarize/", SummarizeAPI.as_view(), name="summarize"),

    # /api/summaries/comic/
    path("comic/", ComicAPI.as_view(), name="comic"),
]
