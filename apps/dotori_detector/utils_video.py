# apps/dotori_detector/utils_video.py

import logging
import tempfile
from typing import Any, Dict, Tuple, Optional, List
import numpy as np
import cv2

from .utils_image_local_ai import analyze_frame_local_ai
from .utils_image import _normalize_probability

log = logging.getLogger(__name__)


#
#  안정적인 프레임 추출 (OpenCV VideoCapture)
#
def extract_frames_opencv(video_bytes: bytes, num_frames: int = 8) -> List[np.ndarray]:
    frames = []

    # 1) 업로드된 바이트를 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        tmp.write(video_bytes)
        tmp.flush()

        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            log.error("⚠ OpenCV cannot open video")
            return frames

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            log.error("⚠ Video has no frames")
            cap.release()
            return frames

        # 골고루 추출하기 위한 인덱스 계산
        idxs = np.linspace(0, frame_count - 1, num_frames).astype(int)

        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok and frame is not None:
                frames.append(frame)
            else:
                log.warning(f"⚠ Failed to read frame at index {idx}")

        cap.release()

    return frames


#
#  프레임마다 AI 탐지 → 평균 확률 계산
#
def _call_local_video_detector(video_bytes: bytes) -> Dict[str, Any]:
    out = {
        "source": "local_video_ai",
        "score": None,
        "label": "unknown",
        "raw": {},
        "error": None,
    }

    try:
        frames = extract_frames_opencv(video_bytes)

        if not frames:
            out["error"] = "no_frames_extracted"
            return out

        scores = []
        raw_frames = []

        for f in frames:
            sc, detail = analyze_frame_local_ai(f)
            raw_frames.append(detail)
            if sc is not None:
                scores.append(sc)

        if not scores:
            out["error"] = "no_valid_frame_scores"
            return out

        avg = float(sum(scores) / len(scores))
        avg = _normalize_probability(avg)

        out["score"] = avg
        out["label"] = "ai" if avg >= 0.5 else "real"
        out["raw"] = {
            "frame_scores": scores,
            "frame_details": raw_frames,
            "num_frames": len(scores),
        }

    except Exception as e:
        log.exception("Local video AI detection failed")
        out["error"] = str(e)

    return out


#
#  views.py와 호환되는 detect_video_ai()
#
def detect_video_ai(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    pos = file_obj.tell()
    blob = file_obj.read()
    file_obj.seek(pos)

    se = _call_local_video_detector(blob)
    score = se.get("score")

    detail = {
        "sources": [se],
        "ensemble": {
            "method": "local_video_ai_mean",
            "ai_probability": score,
            "num_sources": 1,
        },
        "error": se.get("error"),
    }

    return score, detail


#
#  views.py가 그대로 사용 가능한 API 구조 유지
#
def video_detector_score(file_obj) -> Tuple[Optional[float], Dict[str, Any]]:
    score, base_detail = detect_video_ai(file_obj)
    se = base_detail["sources"][0]

    hf = {
        "score": se.get("score"),
        "label": se.get("label"),
        "raw": se.get("raw"),
        "error": se.get("error"),
    }

    detail = {
        "free": {"avg": None, "frames": 0},
        "hf": hf,
        "sources": base_detail["sources"],
        "ensemble": base_detail["ensemble"],
        "error": base_detail.get("error"),
    }

    return score, detail
