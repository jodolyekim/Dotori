from rest_framework import generics, permissions
from .models import Summary
from .serializers import SummaryCreateSerializer, SummarySerializer
from .tasks import run_summary
class SummaryCreateView(generics.CreateAPIView):
    serializer_class = SummaryCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user, status="PENDING")
        run_summary.delay(obj.id)
class SummaryDetailView(generics.RetrieveAPIView):
    serializer_class = SummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Summary.objects.all()
class MySummariesView(generics.ListAPIView):
    serializer_class = SummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Summary.objects.filter(owner=self.request.user).order_by("-created_at")
