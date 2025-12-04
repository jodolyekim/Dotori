# apps/dotori_detector/utils_text.py
import os
import json
import logging
from typing import Any, Dict, Tuple, Optional, List

import requests

log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# 환경변수 (GPTZero 전용)
# ─────────────────────────────────────────
GPTZERO_API_KEY = os.getenv("GPTZERO_API_KEY", "").strip()
GPTZERO_API_URL = os.getenv(
    "GPTZERO_API_URL",
    "https://api.gptzero.me/v2/predict/text",  # 공식 문서 기준
).strip()
GPTZERO_VERSION = os.getenv("GPTZERO_VERSION", "").strip()            # 선택 사항
GPTZERO_MULTILINGUAL = os.getenv("GPTZERO_MULTILINGUAL", "").strip()  # "true"/"false" 선택 사항


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _normalize_probability(p: Optional[float]) -> Optional[float]:
    """
    0~1로 클램프 + 0.49~0.51 구간에서 50% 딱 반반 피하기.
    그리고 1.0(100%)는 안 나오게 상한선 0.98로 캡.
    """
    if p is None:
        return None
    p = _clamp01(p)

    # 50% 근처면 살짝 기울이기
    if 0.49 <= p <= 0.51:
        p = 0.501 if p >= 0.5 else 0.499

    # "백프로"는 없게 0.98으로 상한선
    if p > 0.98:
        p = 0.98

    return p


# ─────────────────────────────────────────
# GPTZero 호출 (공용)
# ─────────────────────────────────────────
def _call_gptzero(text: str) -> Dict[str, Any]:
    """
    GPTZero 텍스트 감지 호출.
    """
    out: Dict[str, Any] = {
        "source": "gptzero",
        "score": None,
        "label": "unknown",
        "reason": None,
        "raw": None,
        "error": None,
    }

    if not GPTZERO_API_KEY or not GPTZERO_API_URL:
        out["error"] = "GPTZero not configured"
        return out

    try:
        headers = {
            "x-api-key": GPTZERO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # ✅ 공식 예시 기준: document는 "문자열" 그대로 전달
        payload: Dict[str, Any] = {
            "document": text,
        }
        if GPTZERO_VERSION:
            payload["version"] = GPTZERO_VERSION
        if GPTZERO_MULTILINGUAL:
            payload["multilingual"] = GPTZERO_MULTILINGUAL

        r = requests.post(
            GPTZERO_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )

        # 상태 코드 체크 (400 등 디버깅용)
        if r.status_code != 200:
            try:
                log.error("GPTZero bad response: %s %s", r.status_code, r.text)
                out["raw"] = {"status_code": r.status_code, "body": r.text}
            except Exception:
                log.error("GPTZero bad response: %s (no body)", r.status_code)
                out["raw"] = {"status_code": r.status_code}
            out["error"] = f"HTTP {r.status_code}"
            return out

        data = r.json()
        out["raw"] = data

        # ───── GPTZero 응답 파싱 ─────
        doc = None
        docs = data.get("documents")
        if isinstance(docs, list) and docs:
            doc = docs[0]

        ai_prob = None
        if isinstance(doc, dict):
            # 공식 문서 기준: completely_generated_prob
            ai_prob = doc.get("completely_generated_prob")

        if isinstance(ai_prob, (int, float)):
            score = _normalize_probability(ai_prob)
            out["score"] = score
            out["label"] = "ai" if score >= 0.5 else "human"
            out["reason"] = "GPTZero completely_generated_prob"
        else:
            out["error"] = "no completely_generated_prob in GPTZero response"

    except Exception as e:
        log.exception("GPTZero request failed")
        out["error"] = str(e)

    return out


def detect_text_ai(text: str) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    텍스트가 AI 생성일 확률 추정 (0~1).
    GPTZero 단독 사용.
    """
    source = _call_gptzero(text)

    if isinstance(source.get("score"), (int, float)):
        ai_prob: Optional[float] = _normalize_probability(source["score"])
    else:
        ai_prob = None

    detail: Dict[str, Any] = {
        "sources": [source],  # GPTZero 1개만
        "ensemble": {
            "method": "single_gptzero",
            "ai_probability": ai_prob,
            "num_sources": 1 if ai_prob is not None else 0,
        },
        "error": source.get("error"),
    }

    return ai_prob, detail


# ─────────────────────────────────────────
# DetectTextView에서 쓰는 인터페이스
#   - openai_judge_score (GPTZero 래퍼)
#   (무료 DetectGPT-lite는 제거)
# ─────────────────────────────────────────
def openai_judge_score(text: str) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    DetectTextView에서 사용하는 GPTZero 래퍼.

    반환 형식: (score, detail_dict)
      - score: 0~0.98 사이의 float 또는 None
      - detail_dict["reasons"]: [str, ...] (한국어 설명 조립용)
      - detail_dict["gptzero_detail"]: detect_text_ai의 detail 그대로
    """
    ai_prob, gptzero_detail = detect_text_ai(text)

    # reasons 구성
    reasons: List[str] = []
    src_list = gptzero_detail.get("sources") or []
    if src_list and isinstance(src_list, list):
        s0 = src_list[0]
        if isinstance(s0, dict):
            s_score = s0.get("score")
            s_label = s0.get("label")
            s_reason = s0.get("reason")
            if isinstance(s_score, (int, float)):
                reasons.append(f"GPTZero score={round(float(s_score), 3)}")
            if isinstance(s_label, str):
                reasons.append(f"GPTZero label={s_label}")
            if isinstance(s_reason, str):
                reasons.append(f"GPTZero reason={s_reason}")

    detail: Dict[str, Any] = {
        "reasons": reasons,
        "gptzero_detail": gptzero_detail,
    }

    return ai_prob, detail
