# apps/dotori_detector/utils_audio.py
import os
import io
import wave
import logging
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import requests

log = logging.getLogger(__name__)

AURIGIN_API_KEY = os.getenv("AURIGIN_API_KEY", "").strip()
AURIGIN_API_URL = os.getenv(
    "AURIGIN_API_URL",
    "https://aurigin.ai/api-ext/predict",  # 예시, 실제 endpoint 확인 필요
).strip()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _normalize_probability(p: Optional[float]) -> Optional[float]:
    if p is None:
        return None
    p = _clamp01(p)
    if 0.49 <= p <= 0.51:
        if p >= 0.5:
            p = 0.501
        else:
            p = 0.499
    return p


def _read_wav_mono16k_from_file(file_obj) -> bytes:
    """
    Aurigin에 바로 보낼 수 있는 WAV(16k, mono) 포맷이 아니어도
    여기서 ffmpeg 변환 등을 걸어도 되지만,
    일단은 업로드된 파일이 이미 wav라고 가정.
    필요하다면 기존 ffmpeg 로직을 참고해서 확장 가능.
    """
    pos = file_obj.tell()
    blob = file_obj.read()
    file_obj.seek(pos)
    return blob


def _local_audio_heuristic(wav_bytes: bytes) -> Optional[float]:
    """
    간단한 로컬 휴리스틱 (에너지, zero-crossing 등).
    Aurigin 보조로만 사용.
    """
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            ch = w.getnchannels()
            sr = w.getframerate()
            n = w.getnframes()
            pcm = w.readframes(n)
        data = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
        if sr <= 0 or data.size == 0:
            return None
        abs_mean = float(np.mean(np.abs(data)))
        zcr = float(np.mean(np.abs(np.diff(np.sign(data)))))  # 0~2
        s = 0.4 * (abs_mean * 5.0) + 0.6 * min(1.0, zcr)
        return _clamp01(s)
    except Exception:
        return None


def _call_aurigin_audio(wav_bytes: bytes) -> Dict[str, Any]:
    """
    Aurigin 오디오 딥페이크/AI 감지 호출.
    """
    out: Dict[str, Any] = {
        "source": "aurigin",
        "score": None,
        "label": "unknown",
        "reason": None,
        "raw": None,
        "error": None,
    }
    if not (AURIGIN_API_KEY and AURIGIN_API_URL):
        out["error"] = "Aurigin not configured"
        return out

    try:
        headers = {
            "x-api-key": AURIGIN_API_KEY,
        }
        files = {
            "file": ("audio.wav", wav_bytes, "audio/wav"),
        }
        # TODO: 실제 Aurigin API 문서에 맞게 추가 파라미터 구성
        r = requests.post(AURIGIN_API_URL, headers=headers, files=files, timeout=60)
        r.raise_for_status()
        data = r.json()
        out["raw"] = data

        # TODO: 실제 응답 구조에 맞게 파싱
        # 예: {"probabilities": {"deepfake": 0.9, "bonafide": 0.1}, ...}
        ai_prob = None
        probs = data.get("probabilities") if isinstance(data, dict) else None
        if isinstance(probs, dict):
            ai_prob = probs.get("deepfake") or probs.get("ai") or probs.get("fake")

        if isinstance(ai_prob, (int, float)):
            score = _normalize_probability(float(ai_prob))
            out["score"] = score
            out["label"] = "ai" if score >= 0.5 else "human"
            out["reason"] = "Aurigin deepfake probability"
        else:
            out["error"] = "no deepfake prob in Aurigin response"
    except Exception as e:
        log.exception("Aurigin request failed")
        out["error"] = str(e)

    return out


def detect_audio_ai(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    오디오가 AI/딥페이크일 확률 추정 (코어 로직).
    """
    wav_bytes = _read_wav_mono16k_from_file(file_obj)

    sources: List[Dict[str, Any]] = []

    # 로컬 휴리스틱 (보조)
    local_score = _local_audio_heuristic(wav_bytes)
    sources.append({
        "source": "local_audio_heuristic",
        "score": local_score,
        "label": "ai" if (isinstance(local_score, (int, float)) and local_score >= 0.5) else "human",
        "reason": "local energy/zcr heuristic" if local_score is not None else None,
        "raw": None,
        "error": None if local_score is not None else "could not compute",
    })

    # Aurigin
    sources.append(_call_aurigin_audio(wav_bytes))

    valid_scores = [s["score"] for s in sources if isinstance(s.get("score"), (int, float))]
    if not valid_scores:
        detail = {
            "sources": sources,
            "ensemble": None,
            "error": "no valid scores from audio detectors",
        }
        return None, detail

    avg = sum(valid_scores) / len(valid_scores)
    ai_prob = _normalize_probability(avg)
    detail = {
        "sources": sources,
        "ensemble": {
            "method": "mean",
            "ai_probability": ai_prob,
            "num_sources": len(valid_scores),
        },
        "error": None,
    }
    return ai_prob, detail


def audio_fake_score_any(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    DetectAudioView에서 사용하는 래퍼.

    views.DetectAudioView 기대 형식:
        score, detail = audio_fake_score_any(up)

        free = detail.get("free", {})
        hf   = detail.get("hf", {})
        free_score = free.get("score")
        paid_score = hf.get("score")

    여기서:
        - free  -> 로컬 휴리스틱(local_audio_heuristic)
        - hf    -> Aurigin 결과
    """
    ai_prob, raw_detail = detect_audio_ai(file_obj)

    raw_detail = raw_detail or {}
    sources = raw_detail.get("sources") or []
    ensemble = raw_detail.get("ensemble")
    error = raw_detail.get("error")

    local: Dict[str, Any] = {}
    aurigin: Dict[str, Any] = {}

    for s in sources:
        if not isinstance(s, dict):
            continue
        src = s.get("source")
        if src == "local_audio_heuristic":
            local = s
        elif src == "aurigin":
            aurigin = s

    free: Dict[str, Any] = {
        "score": local.get("score"),
        "reason": local.get("reason"),
        "error": local.get("error"),
    }

    detail: Dict[str, Any] = {
        "free": free,
        "hf": aurigin,
        "sources": sources,
        "ensemble": ensemble,
        "error": error,
    }
    return ai_prob, detail
