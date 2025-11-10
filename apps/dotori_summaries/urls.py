from django.urls import path
from .views import SummaryCreateView, SummaryDetailView, MySummariesView
urlpatterns = [
    path("", MySummariesView.as_view(), name="my_summaries"),
    path("create/", SummaryCreateView.as_view(), name="create_summary"),
    path("<int:pk>/", SummaryDetailView.as_view(), name="summary_detail"),
]
