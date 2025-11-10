from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
class QuizViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    @action(detail=False, methods=["get"])
    def sample(self, request):
        sample = {
            "title": "문맥 이해 샘플",
            "questions": [
                {"q":"사과는 어디에 속하나요?","choices":["과일","동물","도시"],"answer_index":0,"explain":"사과는 과일입니다"},
            ]
        }
        return Response(sample)
