# apps/dotori_summaries/utils_images.py
import os
import uuid
import logging
import requests
import unicodedata

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

log = logging.getLogger(__name__)

# ───────────── 유틸 ─────────────
def _clean_env(v: str | None) -> str:
    if not v:
        return ""
    return v.split("#", 1)[0].strip()

def _ascii_only(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    return "".join(ch for ch in s if ord(ch) < 128)

def _resolve_api_url(raw: str) -> str:
    if not raw:
        return raw
    fixed = raw.strip()
    # 옛 API 호스트를 새 라우터로 강제 교정
    if "api-inference.huggingface.co" in fixed:
        fixed = fixed.replace(
            "https://api-inference.huggingface.co/models",
            "https://router.huggingface.co/hf-inference/models",
        )
    return fixed

def _parse_size(size_str: str | None, fallback=(512, 512)) -> tuple[int, int]:
    """'512x512' → (512, 512)"""
    if not size_str:
        return fallback
    try:
        w, h = size_str.lower().replace(" ", "").split("x", 1)
        w, h = int(w), int(h)
        # FLUX는 대체로 32배수 권장
        w = max(64, (w // 32) * 32)
        h = max(64, (h // 32) * 32)
        return (w, h)
    except Exception:
        return fallback

def _save_image_bytes(img_bytes: bytes, ext="png") -> str:
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = f"ai_images/{fname}"
    default_storage.save(path, ContentFile(img_bytes))
    return settings.MEDIA_URL + path

# ───────────── ENV ─────────────
HF_API_URL   = _resolve_api_url(_clean_env(os.getenv("HF_API_URL")))
HF_API_KEY   = _clean_env(os.getenv("HF_API_KEY"))
HF_TIMEOUT   = int(_clean_env(os.getenv("HF_TIMEOUT")) or "60")
HF_STEPS     = int(_clean_env(os.getenv("HF_STEPS")) or "6")
HF_GUIDANCE  = float(_clean_env(os.getenv("HF_GUIDANCE")) or "1.0")

# ───────────── 메인 함수 ─────────────
def generate_images_hf(prompt: str, n: int = 4, size: str = "512x512") -> list[str]:
    """
    Hugging Face Router (Text-to-Image: FLUX 등) 호출
      - inputs: prompt (str)
      - parameters: width/height/num_inference_steps/guidance_scale
      - Accept: image/png → 이미지 바이트를 받아 /media 저장
    """
    if not HF_API_KEY or not HF_API_URL:
        raise RuntimeError("HF_API_KEY/HF_API_URL 미설정")

    width, height = _parse_size(size, fallback=(512, 512))

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Accept": "image/png",
        "Content-Type": "application/json",
        "X-Wait-For-Model": "true",
    }
    safe_headers = {k: _ascii_only(v) for k, v in headers.items()}
    for k, v in headers.items():
        if v != safe_headers[k]:
            log.warning("[HF HEADERS] sanitized %s: %r -> %r", k, v, safe_headers[k])

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
            "num_inference_steps": HF_STEPS,
            "guidance_scale": HF_GUIDANCE,
            # "seed": 0,  # 필요 시 고정 시드
        },
        "options": {"wait_for_model": True},
    }

    api_url = _resolve_api_url(HF_API_URL)
    log.debug("[HF CALL] url=%s w=%s h=%s steps=%s guide=%s", api_url, width, height, HF_STEPS, HF_GUIDANCE)

    results: list[str] = []
    for i in range(n):
        r = requests.post(api_url, headers=safe_headers, json=payload, timeout=HF_TIMEOUT)
        ct = r.headers.get("Content-Type", "")
        if r.status_code == 200 and ct.startswith("image/"):
            ext = "png" if "png" in ct else ("jpg" if "jpeg" in ct else "img")
            url = _save_image_bytes(r.content, ext=ext)
            results.append(url)
        else:
            body = (r.text or "")[:800]
            log.error("[HF ERROR] status=%s ct=%s body=%s", r.status_code, ct, body)
            raise RuntimeError(f"HuggingFace error {r.status_code}")
    return results
