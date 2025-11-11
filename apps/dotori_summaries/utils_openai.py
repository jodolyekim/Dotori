# apps/dotori_summaries/utils_openai.py
import os
import uuid
import base64
import requests
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()

# ======================
# 🔧 공통 환경 설정
# ======================
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_ORG_ID   = os.getenv("OPENAI_ORG_ID", "")

# === Hugging Face 설정 ===
HF_TOKEN  = os.getenv("HF_TOKEN", "")
HF_MODEL  = os.getenv("HF_MODEL", "black-forest-labs/FLUX.1-schnell")
HF_STEPS  = int(str(os.getenv("HF_STEPS", "6")).split("#")[0].strip())   # 6~8 권장
HF_GUIDE  = float(str(os.getenv("HF_GUIDANCE", "1.0")).split("#")[0].strip())

# === 이미지 공급자 ===
# OPENAI | HUGGINGFACE | MOCK | DISABLED
IMAGE_PROVIDER  = os.getenv("IMAGE_PROVIDER", "OPENAI").upper()
IMAGE_RETURN_FORMAT = os.getenv("IMAGE_RETURN_FORMAT", "url").lower()  # url | b64

# === 타임아웃(초) ===
CHAT_TIMEOUT   = int(os.getenv("OPENAI_CHAT_TIMEOUT", "60"))
IMAGE_TIMEOUT  = int(os.getenv("OPENAI_IMAGE_TIMEOUT", "120"))
VISION_TIMEOUT = int(os.getenv("OPENAI_VISION_TIMEOUT", "60"))

# ======================
# 🧩 placeholder 유틸 (1×1 투명 PNG)
# ======================
_PLACEHOLDER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)

def _ensure_placeholder_and_get_relurl() -> str:
    """media/ai_images/placeholder.png이 없으면 생성하고, 상대 URL을 반환"""
    save_dir = os.path.join(settings.MEDIA_ROOT, "ai_images")
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "placeholder.png")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(base64.b64decode(_PLACEHOLDER_B64))
    return f"{settings.MEDIA_URL}ai_images/placeholder.png"

# ======================
# 🔧 헤더
# ======================
def _headers_openai():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다 (.env 확인).")
    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    if OPENAI_ORG_ID:
        h["OpenAI-Organization"] = OPENAI_ORG_ID
    return h

def _headers_hf():
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN 이 설정되지 않았습니다 (.env 확인).")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}"
    }

# ======================
# 🤖 클라이언트
# ======================
class OpenAIClient:
    # === CHAT (요약/대화) ===
    def chat(self, model: str, messages: list, max_tokens: int = 512):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        r = requests.post(url, headers=_headers_openai(), json=payload, timeout=CHAT_TIMEOUT)
        if r.status_code >= 400:
            raise RuntimeError(f"[CHAT ERR {r.status_code}] {r.text}")
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

    # === IMAGE GENERATE ===
    def image_generate(self, model: str, prompt: str, size: str = "512x512", n: int = 4):
        """
        - OPENAI     : DALL·E API(URL 반환)
        - HUGGINGFACE: FLUX.1-schnell → 파일 저장 후 URL 반환 (dummy 자동 재시도)
        - MOCK       : picsum.photos 랜덤 이미지
        """
        print(f"DEBUG: IMAGE_PROVIDER={IMAGE_PROVIDER}, RETURN_FORMAT={IMAGE_RETURN_FORMAT}", flush=True)

        if IMAGE_PROVIDER == "DISABLED":
            raise RuntimeError("IMAGE_PROVIDER=DISABLED")

        # MOCK
        if IMAGE_PROVIDER == "MOCK":
            w, h = size.split("x")
            return [f"https://picsum.photos/seed/{uuid.uuid4()}/{w}/{h}" for _ in range(int(n))]

        # OPENAI
        if IMAGE_PROVIDER == "OPENAI":
            url = f"{OPENAI_BASE_URL}/images/generations"
            payload = {"model": model, "prompt": prompt, "size": size, "n": n}
            r = requests.post(url, headers=_headers_openai(), json=payload, timeout=IMAGE_TIMEOUT)
            if r.status_code >= 400:
                raise RuntimeError(f"[IMAGE ERR {r.status_code}] {r.text}")
            data = r.json().get("data", [])
            return [item.get("url") for item in data if "url" in item]

        # HUGGING FACE
        if IMAGE_PROVIDER == "HUGGINGFACE":
            try:
                w, h = map(int, size.lower().split("x"))
            except Exception:
                w, h = 512, 512

            api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
            payload = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": HF_STEPS,
                    "guidance_scale": HF_GUIDE,
                    "width": w,
                    "height": h,
                },
                "options": {"wait_for_model": True},  # 웜업 보장
            }

            out = []
            save_dir = os.path.join(settings.MEDIA_ROOT, "ai_images")
            os.makedirs(save_dir, exist_ok=True)
            placeholder_rel = _ensure_placeholder_and_get_relurl()

            for i in range(int(n)):
                for attempt in range(3):  # 최대 3회 재시도
                    r = requests.post(api_url, headers=_headers_hf(), json=payload, timeout=IMAGE_TIMEOUT)
                    ctype = r.headers.get("content-type", "")
                    # 정상 이미지: image/* + 2KB 이상
                    if r.status_code == 200 and ctype.startswith("image/") and len(r.content) > 2000:
                        ext = "png" if "png" in ctype else "jpg"
                        filename = f"{uuid.uuid4()}.{ext}"
                        path = os.path.join(save_dir, filename)
                        with open(path, "wb") as f:
                            f.write(r.content)
                        out.append(f"{settings.MEDIA_URL}ai_images/{filename}")
                        print(f"[HF OK] panel {i+1} ({len(r.content)} bytes)")
                        break
                    else:
                        print(f"[HF RETRY {attempt+1}] {r.status_code} len={len(r.content)}")
                        if attempt == 2:
                            # 3회 실패 → 유효한 PNG placeholder 반환
                            out.append(placeholder_rel)
                # end attempt
            return out

        raise RuntimeError(f"Unknown IMAGE_PROVIDER={IMAGE_PROVIDER}")

    # === VISION → TEXT ===
    def vision_to_text(self, model: str, image_b64: str, prompt: str = "Extract Korean text", mime: str = "image/png"):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}" }},
            ],
        }]
        payload = {"model": model, "messages": messages}
        r = requests.post(url, headers=_headers_openai(), json=payload, timeout=VISION_TIMEOUT)
        if r.status_code >= 400:
            raise RuntimeError(f"[VISION ERR {r.status_code}] {r.text}")
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

# 전역 인스턴스
client = OpenAIClient()
