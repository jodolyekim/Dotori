from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, parsers

from .utils_image import image_detector_score
from .utils_video import video_detector_score
from .utils_audio import audio_fake_score_any
from .utils_text import openai_judge_score  # GPTZero


class AuthRequired(permissions.IsAuthenticated):
    pass


def _norm_score(obj):
    if obj is None:
        return {"score": None, "error": None, "raw": None}

    if isinstance(obj, dict):
        s = obj.get("score")
        return {
            "score": float(s) if isinstance(s, (int, float)) else None,
            "error": obj.get("error"),
            "raw": obj
        }

    if isinstance(obj, (list, tuple)) and obj:
        s = obj[0]
        return {
            "score": float(s) if isinstance(s, (int, float)) else None,
            "error": None,
            "raw": obj
        }

    if isinstance(obj, (int, float)):
        return {"score": float(obj), "error": None, "raw": obj}

    return {
        "score": None,
        "error": f"unsupported type: {type(obj).__name__}",
        "raw": obj
    }


def _ko_join_reasons(*reasons):
    arr = [r for r in reasons if isinstance(r, str) and r.strip()]
    return " / ".join(arr) if arr else None


# -------------------------
# TEXT (GPTZero)
# -------------------------
class DetectTextView(APIView):
    permission_classes = [AuthRequired]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "text is required"}, status=400)

        try:
            paid_raw = openai_judge_score(text)
        except Exception as e:
            paid_raw = {"score": None, "error": str(e)}

        paid = _norm_score(paid_raw)
        score = paid["score"]

        explain_ko = None
        if isinstance(paid["raw"], (list, tuple)) and len(paid["raw"]) >= 2:
            detail = paid["raw"][1]
            if isinstance(detail, dict):
                rs = detail.get("reasons", [])
                if isinstance(rs, list) and rs:
                    explain_ko = "GPTZero 판별 사유: " + " | ".join(rs)

        return Response({
            "type": "text",
            "score": score,
            "paid_score": score,
            "free_score": None,
            "explain": {
                "free": None,
                "paid": paid,
                "explain_ko": explain_ko,
            }
        })


# -------------------------
# IMAGE (Sightengine)
# -------------------------
class DetectImageView(APIView):
    permission_classes = [AuthRequired]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        up = request.FILES.get("file") or request.FILES.get("image")
        if not up:
            return Response({"detail": "image (file) is required"}, status=400)

        try:
            score, detail = image_detector_score(up)

            hf = detail.get("hf", {})
            explain_ko = f"SightEngine(label={hf.get('label')}, score={hf.get('score')})"

            return Response({
                "type": "image",
                "score": score,
                "paid_score": hf.get("score"),
                "free_score": None,
                "explain": {
                    "detail": detail,
                    "explain_ko": explain_ko,
                }
            })

        except Exception as e:
            return Response({
                "type": "image",
                "score": None,
                "paid_score": None,
                "free_score": None,
                "explain": {"error": str(e)},
            })


# -------------------------
# AUDIO (Aurigin 유지)
# -------------------------
class DetectAudioView(APIView):
    permission_classes = [AuthRequired]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        up = request.FILES.get("audio") or request.FILES.get("file")
        if not up:
            return Response({"detail": "audio (file) is required"}, status=400)

        try:
            score, detail = audio_fake_score_any(up)

            free = detail.get("free", {})
            hf = detail.get("hf", {})

            free_score = free.get("score")
            paid_score = hf.get("score")

            parts = []
            if free_score is not None:
                parts.append(f"로컬 휴리스틱={round(free_score, 3)}")
            if paid_score is not None:
                parts.append(f"Aurigin(label={hf.get('label')}, score={paid_score})")

            explain_ko = " / ".join(parts) if parts else None

            return Response({
                "type": "audio",
                "score": score,
                "paid_score": paid_score,
                "free_score": free_score,
                "explain": {
                    "detail": detail,
                    "explain_ko": explain_ko,
                }
            })

        except Exception as e:
            return Response({
                "type": "audio",
                "score": None,
                "paid_score": None,
                "free_score": None,
                "explain": {"error": str(e)},
            })


# -------------------------
# VIDEO (Sightengine)
# -------------------------
class DetectVideoView(APIView):
    permission_classes = [AuthRequired]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        up = request.FILES.get("video") or request.FILES.get("file")
        if not up:
            return Response({"detail": "video (file) is required"}, status=400)

        try:
            score, detail = video_detector_score(up)

            hf = detail.get("hf", {})
            explain_ko = f"SightEngine(label={hf.get('label')}, score={hf.get('score')})"

            return Response({
                "type": "video",
                "score": score,
                "paid_score": hf.get("score"),
                "free_score": None,
                "explain": {
                    "detail": detail,
                    "explain_ko": explain_ko,
                }
            })

        except Exception as e:
            return Response({
                "type": "video",
                "score": None,
                "paid_score": None,
                "free_score": None,
                "explain": {"error": str(e)},
            })
