import io
import logging
from typing import Any, Dict, List, Tuple, Optional

from PIL import Image
import requests
from django.conf import settings

log = logging.getLogger(__name__)

API_USER = getattr(settings, "SIGHTENGINE_API_USER", None)
API_SECRET = getattr(settings, "SIGHTENGINE_API_SECRET", None)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _normalize_probability(p: Optional[float]) -> Optional[float]:
    if p is None:
        return None
    p = _clamp01(p)
    if 0.49 <= p <= 0.51:
        p = 0.501 if p >= 0.5 else 0.499
    if p > 0.98:
        p = 0.98
    return p


def _image_to_jpeg_bytes(file_obj) -> bytes:
    pos = file_obj.tell()
    try:
        img = Image.open(file_obj).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return buf.getvalue()
    finally:
        file_obj.seek(pos)


def _call_sightengine_image(jpeg_bytes: bytes) -> Dict[str, Any]:
    """
    Sightengine 이미지 판별 호출 + score 계산
    """
    out = {
        "source": "sightengine_image",
        "score": None,
        "label": "unknown",
        "raw": None,
        "error": None,
    }

    try:
        files = {"media": ("image.jpg", jpeg_bytes, "image/jpeg")}
        data = {
            "models": "genai",  # ★ 핵심 수정
            "api_user": API_USER,
            "api_secret": API_SECRET,
        }

        res = requests.post(
            "https://api.sightengine.com/1.0/check.json",
            data=data,
            files=files,
            timeout=20,
        )
        raw = res.json()
        out["raw"] = raw

        typeinfo = raw.get("type") or {}
        ai_prob = None

        if isinstance(typeinfo, dict):
            v = typeinfo.get("ai_generated")
            if isinstance(v, (int, float)):
                ai_prob = float(v)

        if ai_prob is not None:
            out["score"] = _normalize_probability(ai_prob)
            out["label"] = "ai" if ai_prob >= 0.5 else "real"

    except Exception as e:
        log.exception("SightEngine image request failed")
        out["error"] = str(e)

    return out


def detect_image_ai(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    jpeg_bytes = _image_to_jpeg_bytes(file_obj)
    se = _call_sightengine_image(jpeg_bytes)
    score = se.get("score")

    detail = {
        "sources": [se],
        "ensemble": {
            "method": "single_sightengine",
            "ai_probability": score,
            "num_sources": 1,
        },
        "error": se.get("error"),
    }

    return score, detail


def image_detector_score(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    score, base_detail = detect_image_ai(file_obj)
    se = base_detail["sources"][0]

    hf = {
        "score": se.get("score"),
        "label": se.get("label"),
        "raw": se.get("raw"),
        "error": se.get("error"),
    }

    detail = {
        "free": {},
        "hf": hf,
        "sources": base_detail["sources"],
        "ensemble": base_detail["ensemble"],
        "error": base_detail.get("error"),
    }

    return score, detail
