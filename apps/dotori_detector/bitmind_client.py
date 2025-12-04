# apps/dotori_detector/bitmind_client.py
import os
import json
from typing import Any, Dict, Optional, Tuple

import requests


# ─────────────────────────────────────
# 환경변수 로드
# ─────────────────────────────────────
BITMIND_API_KEY_RAW = os.getenv("BITMIND_API_KEY", "").strip()

# BitMind 키가 "id:secret" 형식일 수 있어서 secret만 사용
if ":" in BITMIND_API_KEY_RAW:
    BITMIND_API_KEY = BITMIND_API_KEY_RAW.split(":")[-1].strip()
else:
    BITMIND_API_KEY = BITMIND_API_KEY_RAW

# 공식 BASE_URL은 여기까지임 (detect-image 포함하면 절대 안됨)
BITMIND_BASE_URL = "https://api.bitmind.ai/oracle/v1"

# 모델 ID 기본값
BITMIND_MODEL_ID = os.getenv("BITMIND_MODEL_ID", "34").strip()

# 앱 ID (문서 기본값: oracle-api)
BITMIND_APP_ID = os.getenv("BITMIND_APP_ID", "oracle-api").strip() or "oracle-api"

# rich 옵션
BITMIND_RICH = os.getenv("BITMIND_RICH", "true").strip().lower() in {"1", "true", "yes", "y"}

# 정확한 엔드포인트 구성
BITMIND_IMAGE_URL = f"{BITMIND_BASE_URL}/{BITMIND_MODEL_ID}/detect-image"
BITMIND_VIDEO_URL = f"{BITMIND_BASE_URL}/{BITMIND_MODEL_ID}/detect-video"

print("=== [BitMind DEBUG] ENV LOADED ===")
print(f"BITMIND_API_KEY_RAW: '{BITMIND_API_KEY_RAW}'")
print(f"BITMIND_API_KEY    : '{BITMIND_API_KEY}'")
print(f"BITMIND_BASE_URL   : {BITMIND_BASE_URL}")
print(f"BITMIND_MODEL_ID   : {BITMIND_MODEL_ID}")
print(f"BITMIND_APP_ID     : {BITMIND_APP_ID}")
print(f"BITMIND_IMAGE_URL  : {BITMIND_IMAGE_URL}")
print(f"BITMIND_VIDEO_URL  : {BITMIND_VIDEO_URL}")
print("===================================")


# ─────────────────────────────────────
# 공통 헤더
# ─────────────────────────────────────
def _auth_headers() -> Dict[str, str]:
    if not BITMIND_API_KEY:
        raise RuntimeError("BITMIND_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {BITMIND_API_KEY}",
        "Content-Type": "application/json",
        "x-bitmind-application": BITMIND_APP_ID,
        "Accept": "application/json",
    }

    print("=== [BitMind DEBUG] AUTH HEADERS ===")
    masked = BITMIND_API_KEY[:4] + "..." if BITMIND_API_KEY else ""
    print({
        "Authorization": f"Bearer {masked}",
        "x-bitmind-application": BITMIND_APP_ID,
    })
    print("====================================")

    return headers


def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {
            "raw_text": resp.text[:1000],
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
        }


def _extract_score_label(raw: Dict[str, Any]) -> Tuple[Optional[float], str, Optional[str]]:
    if not isinstance(raw, dict):
        return None, "unknown", None

    node = raw

    # unwrap result/oracle
    result = node.get("result")
    if isinstance(result, dict):
        node = result.get("oracle") or result

    score = None
    label = "unknown"
    reason = None

    conf = node.get("confidence")
    if isinstance(conf, (int, float)):
        score = float(conf)

    is_ai = node.get("isAI")
    if isinstance(is_ai, bool):
        label = "ai" if is_ai else "human"
        if score is None:
            score = 0.9 if is_ai else 0.1
        reason = "BitMind isAI flag"

    lab = node.get("label")
    if isinstance(lab, str):
        l = lab.lower()
        if any(k in l for k in ("fake", "ai", "deepfake", "synthetic")):
            label = "ai"
        elif any(k in l for k in ("real", "human", "authentic", "genuine")):
            label = "human"
        else:
            label = l
        if reason is None:
            reason = f"BitMind label={lab}"

    if score is None:
        scores = node.get("scores") or node.get("probabilities")
        if isinstance(scores, dict):
            ai_val = scores.get("ai") or scores.get("fake")
            if isinstance(ai_val, (int, float)):
                score = float(ai_val)
                if reason is None:
                    reason = "BitMind scores[ai]"

    return score, label, reason


# ─────────────────────────────────────
# 이미지
# ─────────────────────────────────────
def detect_image_from_bytes(jpeg_bytes: bytes) -> Dict[str, Any]:
    out = {
        "source": "bitmind_image",
        "score": None,
        "label": "unknown",
        "reason": None,
        "raw": None,
        "error": None,
        "status_code": None,
    }

    headers = _auth_headers()

    import base64
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")

    payload = {
        "image": f"data:image/jpeg;base64,{b64}",
        "rich": BITMIND_RICH,
    }

    print("=== [BitMind DEBUG] DETECT IMAGE REQUEST ===")
    print(f"URL: {BITMIND_IMAGE_URL}")
    print("===========================================")

    try:
        r = requests.post(
            BITMIND_IMAGE_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        out["status_code"] = r.status_code
        raw = _safe_json(r)
        out["raw"] = raw

        print("=== [BitMind DEBUG] IMAGE RESPONSE ===")
        print(f"Status: {r.status_code}")
        print(f"Raw: {raw}")
        print("======================================")

        if r.status_code < 400:
            score, label, reason = _extract_score_label(raw)
            out["score"] = score
            out["label"] = label
            out["reason"] = reason
        else:
            out["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        out["error"] = f"BitMind image request failed: {e}"

    return out


# ─────────────────────────────────────
# 비디오
# ─────────────────────────────────────
def detect_video_from_bytes(video_bytes: bytes) -> Dict[str, Any]:
    out = {
        "source": "bitmind_video",
        "score": None,
        "label": "unknown",
        "reason": None,
        "raw": None,
        "error": None,
        "status_code": None,
    }

    if len(video_bytes) > 10 * 1024 * 1024:
        out["error"] = "BitMind direct video upload limit is 10MB"
        return out

    headers = _auth_headers()

    try:
        files = {
            "video": ("upload.mp4", video_bytes, "video/mp4"),
        }
        data = {"rich": "true" if BITMIND_RICH else "false"}

        r = requests.post(
            BITMIND_VIDEO_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=180,
        )
        out["status_code"] = r.status_code
        raw = _safe_json(r)
        out["raw"] = raw

        print("=== [BitMind DEBUG] VIDEO RESPONSE ===")
        print(f"Status: {r.status_code}")
        print(f"Raw: {raw}")
        print("======================================")

        if r.status_code < 400:
            score, label, reason = _extract_score_label(raw)
            out["score"] = score
            out["label"] = label
            out["reason"] = reason
        else:
            out["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        out["error"] = str(e)

    return out
