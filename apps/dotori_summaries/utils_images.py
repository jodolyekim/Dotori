# apps/dotori_summaries/utils_images.py
'''
import os
import uuid
import logging
import requests
import unicodedata

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

log = logging.getLogger(__name__)

# ── 유틸 ──
def _clean_env(v: str | None) -> str:
    if not v:
        return ""
    return v.split("#", 1)[0].strip()

def _ascii_only(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    return "".join(ch for ch in s if ord(ch) < 128)

def _parse_size(size_str: str | None, fallback=(512, 512)) -> tuple[int, int]:
    # "512x512" → (512, 512)
    if not size_str:
        return fallback
    try:
        w, h = size_str.lower().replace(" ", "").split("x", 1)
        w, h = int(w), int(h)
        # FLUX 권장: 32 배수 정렬
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

def _map_to_router(url: str) -> str:
    # 구 Inference API 호스트를 Router 경로로 교정 (문제 없으면 그대로 둬도 됨)
    if "api-inference.huggingface.co" in url:
        return url.replace(
            "https://api-inference.huggingface.co/models",
            "https://router.huggingface.co/hf-inference/models",
        )
    return url

# ── ENV 로딩(신/구 키 모두 지원) ──
# 토큰
HF_API_TOKEN = _clean_env(os.getenv("HF_API_TOKEN") or os.getenv("HF_API_KEY"))

# URL 또는 모델ID
HF_IMAGE_URL = _clean_env(os.getenv("HF_IMAGE_URL") or os.getenv("HF_API_URL"))
HF_IMAGE_MODEL_ID = _clean_env(os.getenv("HF_IMAGE_MODEL_ID") or os.getenv("HF_MODEL"))

HF_TIMEOUT  = int(_clean_env(os.getenv("HF_TIMEOUT")) or "60")
HF_STEPS    = int(_clean_env(os.getenv("HF_STEPS")) or "6")
HF_GUIDANCE = float(_clean_env(os.getenv("HF_GUIDANCE")) or "1.0")

def _resolve_api_url() -> str:
    """
    우선순위:
      1) 명시적 URL(HF_IMAGE_URL/HF_API_URL)
      2) 모델ID(HF_IMAGE_MODEL_ID/HF_MODEL) → Inference API URL 조립
    """
    url = HF_IMAGE_URL
    if not url and HF_IMAGE_MODEL_ID:
        url = f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL_ID}"
    if not url:
        raise RuntimeError("HF_IMAGE_URL 또는 HF_IMAGE_MODEL_ID 설정 필요")
    return _map_to_router(url.strip().rstrip("/"))

# ── 메인 ──
def generate_images_hf(prompt: str, n: int = 4, size: str = "512x512") -> list[str]:
    """
    Hugging Face(Text-to-Image, FLUX 등) 호출
    - inputs: prompt (str)
    - parameters: width/height/num_inference_steps/guidance_scale
    - Accept: image/png → 이미지 바이트 저장 후 URL 반환
    필요 ENV(둘 중 하나씩):
      HF_API_TOKEN(또는 HF_API_KEY)
      HF_IMAGE_URL(또는 HF_API_URL)  /  HF_IMAGE_MODEL_ID(또는 HF_MODEL)
    """
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN(HF_API_KEY) 미설정")

    api_url = _resolve_api_url()
    width, height = _parse_size(size, fallback=(512, 512))

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Accept": "image/png",
        "Content-Type": "application/json",
        "X-Wait-For-Model": "true",
    }
    # 헤더 정규화(비ASCII 제거)
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
        },
        "options": {"wait_for_model": True},
    }

    log.debug("[HF CALL] url=%s w=%s h=%s steps=%s guide=%s",
              api_url, width, height, HF_STEPS, HF_GUIDANCE)

    results: list[str] = []
    for _ in range(max(1, n)):
        r = requests.post(api_url, headers=safe_headers, json=payload, timeout=HF_TIMEOUT)
        ct = (r.headers.get("Content-Type") or r.headers.get("content-type") or "")
        if r.status_code == 200 and ct.startswith("image/"):
            ext = "png" if "png" in ct.lower() else ("jpg" if "jpeg" in ct.lower() else "img")
            url = _save_image_bytes(r.content, ext=ext)
            results.append(url)
        else:
            body = (r.text or "")[:800]
            log.error("[HF ERROR] status=%s ct=%s body=%s", r.status_code, ct, body)
            raise RuntimeError(f"HuggingFace error {r.status_code}")

    return results
'''