# apps/dotori_detector/utils_image_local_ai.py

import numpy as np
import cv2
from typing import Tuple, Dict, Optional, Any   # ★★★ 추가됨 ★★★


def _fft_score(frame: np.ndarray) -> float:
    """
    이미지에서 고주파 성분 비율로 AI 생성 여부 추정.
    GAN 이미지 특유의 high-frequency noise 검출.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)

    h, w = magnitude.shape
    center = magnitude[h//2-8:h//2+8, w//2-8:w//2+8]
    outer = magnitude.mean() - center.mean()

    score = np.clip(outer / (magnitude.mean() + 1e-6), 0, 1)
    return float(score)


def _edge_inconsistency(frame: np.ndarray) -> float:
    """
    AI 이미지에서 흔한 경계 부자연스러움 검사.
    """
    edges = cv2.Canny(frame, 100, 200)
    density = edges.mean() / 255.0
    return float(np.clip(density * 1.5, 0, 1))


def analyze_frame_local_ai(frame: np.ndarray) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    한 프레임을 분석하여 AI 생성 확률 반환
    """
    try:
        fft_s = _fft_score(frame)
        edge_s = _edge_inconsistency(frame)

        final = float(np.clip((fft_s * 0.6 + edge_s * 0.4), 0, 1))

        detail = {
            "fft_score": fft_s,
            "edge_score": edge_s,
            "combined": final,
        }

        return final, detail

    except Exception as e:
        return None, {"error": str(e)}
