import os
import logging
import re

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .serializers import (
    SummarizeRequestSerializer,
    ExplainWordSerializer,
)
from .utils_io import ocr_image_to_text
from .utils_openai import (
    generate_summary,
    extract_vocabulary_explained,
    extract_actions,
    detect_doc_type,
    explain_word_meaning,
)
from apps.dotori_memberships.models_analytics import SummaryDetailLog
from apps.dotori_memberships.models import DailyUsage

log = logging.getLogger(__name__)

SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o")
MAX_INPUT_CHARS = 8000


# ============================================
# 긴 글 자동 분할
# ============================================
def split_text_into_chunks(text: str, chunk_size: int = 1200) -> list[str]:
    sentences = re.split(r"(?<=[.!?…\n])", text)
    chunks, current = [], ""

    for s in sentences:
        if len(current) + len(s) > chunk_size:
            chunks.append(current.strip())
            current = s
        else:
            current += s

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ============================================
# Summarize API — 어려운 단어 설명 포함
# ============================================
class SummarizeAPI(APIView):
    """
    POST /api/summaries/summarize/

    응답 형식:
    {
      "summary": "...",
      "vocabulary": [   # 🔥 Flutter와 맞추기 위해 키 이름을 vocabulary 로 통일
        {
          "word": "자본시장법",
          "meaning": "일반적인 뜻",
          "easy_meaning": "아주 쉬운 설명",
          "example": "간단 예문"
        },
        ...
      ],
      "actions": [...],
      "meta": {...}
    }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SummarizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data.get("text")
        image = serializer.validated_data.get("image")
        difficulty = serializer.validated_data.get("difficulty")
        doc_hint = (serializer.validated_data.get("doc_hint") or "").strip()

        summary_type = "text"

        # OCR
        if image:
            try:
                text = ocr_image_to_text(image)
                summary_type = "ocr"
            except Exception as e:
                log.exception("[SummarizeAPI] OCR 실패: %s", e)
                return Response({"detail": "OCR 실패", "error": str(e)}, status=502)

        if not text or len(text.strip()) < 20:
            return Response({"detail": "요약할 텍스트가 너무 짧습니다."}, status=400)

        raw_text = text.strip()
        original_len = len(raw_text)
        used_text = raw_text[:MAX_INPUT_CHARS]

        # 긴 글 분할 요약
        if len(used_text) > 1500:
            chunks = split_text_into_chunks(used_text)
            chunk_results = []

            for c in chunks:
                try:
                    cs = generate_summary(c, difficulty)
                    chunk_results.append(cs)
                except Exception as e:
                    log.warning("[SummarizeAPI] chunk 요약 실패: %s", e)
                    chunk_results.append("")

            merged = "\n".join(chunk_results)
            final_summary = generate_summary(merged, difficulty)
        else:
            final_summary = generate_summary(used_text, difficulty)

        # -------------------------------------------------
        # 어려운 단어 + 쉬운 설명
        # -------------------------------------------------
        try:
            vocabulary = extract_vocabulary_explained(final_summary, difficulty)
        except Exception as e:
            log.warning("[SummarizeAPI] vocabulary_explained 실패: %s", e)
            vocabulary = []

        # -------------------------------------------------
        # 액션 아이템
        # -------------------------------------------------
        try:
            actions = extract_actions(final_summary)
        except Exception:
            actions = []

        # -------------------------------------------------
        # 문서 유형
        # -------------------------------------------------
        try:
            detected_type = detect_doc_type(final_summary)
        except Exception:
            detected_type = doc_hint or ""

        # -------------------------------------------------
        # meta
        # -------------------------------------------------
        summary_len = len(final_summary)
        meta = {
            "original_length": original_len,
            "summary_length": summary_len,
            "compression_ratio": round(summary_len / original_len, 3),
            "difficulty": difficulty,
            "input_type_detected": detected_type,
        }

        # -------------------------------------------------
        # DailyUsage 기록
        # -------------------------------------------------
        if request.user.is_authenticated:
            from django.utils import timezone

            today = timezone.localdate()
            key = {
                "ELEMENTARY": "SUMMARY_ELEM",
                "SECONDARY": "SUMMARY_SECOND",
                "ADULT": "SUMMARY_ADULT",
            }[difficulty]

            obj, _ = DailyUsage.objects.get_or_create(
                user=request.user,
                date=today,
                feature_type=key,
            )
            obj.used_count += 1
            obj.save()

        # -------------------------------------------------
        # SummaryDetailLog 기록
        # -------------------------------------------------
        try:
            if request.user.is_authenticated:
                SummaryDetailLog.objects.create(
                    user=request.user,
                    text_length=original_len,
                    summary_type=summary_type,
                    category=difficulty,
                )
        except Exception as e:
            log.warning("[SummarizeAPI] SummaryDetailLog 저장 실패: %s", e)

        return Response(
            {
                "summary": final_summary,
                "vocabulary": vocabulary,   # 🔥 여기 이름이 Flutter와 1:1 매칭
                "actions": actions,
                "meta": meta,
            },
            status=200,
        )


# ============================================
# 단어 클릭 → 쉬운 설명 API
# ============================================
class ExplainWordAPI(APIView):
    """
    POST /api/summaries/word-explain/

    body:
      - word: str
      - difficulty: ELEMENTARY | SECONDARY | ADULT (옵션, 기본 ELEMENTARY)

    response:
      {
        "word": "...",
        "meaning": "...",
        "easy_meaning": "...",
        "example": "..."
      }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ExplainWordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        word = serializer.validated_data["word"]
        difficulty = serializer.validated_data.get("difficulty") or "ELEMENTARY"

        try:
            meaning = explain_word_meaning(word, difficulty)
        except Exception as e:
            return Response(
                {"detail": f"단어 설명 실패: {e}"},
                status=500,
            )

        # explain_word_meaning 이 이미 위 형식의 dict를 리턴함
        return Response(meaning, status=200)
