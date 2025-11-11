import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .serializers import SummarizeRequestSerializer, ComicRequestSerializer
from .utils_io import ocr_image_to_text
from .utils_openai import client
from .utils_images import generate_images_hf  # ✅ 허깅페이스 바이너리 호출 유틸

log = logging.getLogger(__name__)

SUMMARY_MODEL     = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o")
IMAGE_MODEL       = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
IMAGE_PROVIDER    = os.getenv("IMAGE_PROVIDER", "OPENAI").upper()
COMIC_IMAGE_SIZE  = os.getenv("COMIC_IMAGE_SIZE", "512x512")  # 기본 512x512

def split_into_4_korean_captions(summary_text: str) -> list:
    system = "You are a precise assistant that formats text only."
    user = (
        "다음 한국어 요약을 4개의 아주 짧은 한국어 캡션으로 나눠줘. "
        "각 항목은 1줄 이내, 불필요한 수식어 생략, 핵심명사/동사만 남겨. "
        "반드시 아래 형식만 출력:\n"
        "1) ...\n2) ...\n3) ...\n4) ...\n\n"
        f"요약:\n{summary_text}"
    )
    messages = [{"role":"system","content":system},{"role":"user","content":user}]
    raw = client.chat(SUMMARY_MODEL, messages, max_tokens=180)
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    caps = []
    for i in range(1,5):
        pref = f"{i})"
        found = next((l for l in lines if l.startswith(pref)), "")
        caps.append(found.split(")",1)[1].strip() if ")" in found else "")
    defaults = ["문제 제기","핵심 내용","예시/비유","결론/행동"]
    caps = [c if c else defaults[i] for i,c in enumerate(caps)]
    return caps

def build_panel_prompt(panel_idx: int, caption: str) -> str:
    panel_titles = ["문제 제기","핵심 내용","예시/비유","결론/행동"]
    panel_name = panel_titles[panel_idx]
    return (
        "A 2D flat illustration in clean comic style, high contrast, soft color palette, "
        "one consistent main character (same age, hair, outfit across panels), "
        "simple background with clear visual storytelling, "
        "no text, no speech bubbles, no watermarks, no captions.\n"
        f"Panel: {panel_idx+1} - {panel_name}\n"
        f"Scene description derived from Korean caption: \"{caption}\".\n"
        "Emphasize action and mood; uncluttered composition; centered subject; eye-level shot."
    )

class SummarizeAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = SummarizeRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        text   = s.validated_data.get('text')
        image  = s.validated_data.get('image')
        style  = s.validated_data.get('style')
        length = s.validated_data.get('length')

        # ✅ 파일 업로드 제거: file 처리 분기 없음
        if image:
            text = ocr_image_to_text(image)

        if not text or len(text.strip()) < 20:
            return Response({"detail": "요약할 텍스트가 너무 짧습니다."}, status=400)

        style_prompt = {
            'bulleted':  '핵심을 3~6개 불릿으로 간결히.',
            'paragraph': '두 문단 이내로 간결히.',
            'minutes':   '안건/결론/할일 형식으로 정리.'
        }[style]
        length_hint = {
            'one_line': '한 문장으로',
            'short':    '짧게',
            'medium':   '보통 길이로',
            'long':     '자세히'
        }[length]

        messages = [
            {"role":"system","content":"You are a Korean summarizer. Keep facts and numbers; avoid hallucination."},
            {"role":"user","content": f"{length_hint} {style_prompt}\n\n원문:\n{text}"}
        ]
        summary = client.chat(SUMMARY_MODEL, messages, max_tokens=400)
        return Response({"summary": summary}, status=200)

class ComicAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = ComicRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        summary = s.validated_data['summary']

        # 1) 요약 → 4개의 짧은 캡션
        captions = split_into_4_korean_captions(summary)

        # 2) 이미지 생성 (프로바이더 분기)
        try:
            if IMAGE_PROVIDER == "HUGGINGFACE":
                prompt = "\n".join(
                    f"Panel {i+1}: {build_panel_prompt(i, cap)}" for i, cap in enumerate(captions)
                )
                imgs = generate_images_hf(prompt, n=4, size=COMIC_IMAGE_SIZE)
            else:
                imgs = []
                for idx, cap in enumerate(captions):
                    panel_prompt = build_panel_prompt(idx, cap)
                    r = client.image_generate(IMAGE_MODEL, panel_prompt, size=COMIC_IMAGE_SIZE, n=1)
                    if not r or not r[0]:
                        raise RuntimeError("OpenAI image empty")
                    imgs.append(r[0])

        except Exception as e:
            log.exception(f"[COMIC] image generation failed: {e}")
            return Response(
                {
                    "images": [],
                    "provider": IMAGE_PROVIDER,
                    "captions": captions,
                    "size": COMIC_IMAGE_SIZE,
                    "error": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        urls = [u.replace("\n", "") for u in imgs]
        preview = {"images": urls, "captions": captions, "size": COMIC_IMAGE_SIZE, "provider": IMAGE_PROVIDER}
        log.info("DEBUG: comic response preview = %s", preview)
        print("DEBUG: comic response preview =", preview, flush=True)

        return Response(
            {
                "images": urls,
                "provider": IMAGE_PROVIDER,
                "captions": captions,
                "size": COMIC_IMAGE_SIZE
            },
            status=200
        )
