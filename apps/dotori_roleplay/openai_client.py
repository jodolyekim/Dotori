# apps/dotori_roleplay/openai_client.py

import os
import logging
from typing import List, Dict, Any

import requests

log = logging.getLogger(__name__)

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ROLEPLAY_MODEL = os.getenv("OPENAI_ROLEPLAY_MODEL", os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o"))
OPENAI_CHAT_TIMEOUT = int(os.getenv("OPENAI_CHAT_TIMEOUT", "60"))


class OpenAIRoleplayClient:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다 (.env 확인).")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        url = f"{OPENAI_BASE_URL}/chat/completions"
        payload = {
            "model": OPENAI_ROLEPLAY_MODEL,
            "messages": messages,
            "temperature": 0.4,
        }
        resp = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=OPENAI_CHAT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data


client = OpenAIRoleplayClient()
