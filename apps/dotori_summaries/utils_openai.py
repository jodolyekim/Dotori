# apps/dotori_summaries/utils_openai.py
import os
import json
import re
import requests
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()

# ======================
# 🔧 공통 환경 설정
# ======================
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID", "")

SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o")

CHAT_TIMEOUT = int(os.getenv("OPENAI_CHAT_TIMEOUT", "60"))
VISION_TIMEOUT = int(os.getenv("OPENAI_VISION_TIMEOUT", "60"))


# ======================
# 🔧 헤더
# ======================
def _headers_openai():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 미설정")
    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    if OPENAI_ORG_ID:
        h["OpenAI-Organization"] = OPENAI_ORG_ID
    return h


# ======================
# 🔧 JSON 파싱 보조 함수
# ======================
def _extract_json_array(raw: str):
    """
    모델이 ```json ... ``` 같은 형식으로 줘도
    내부의 JSON 배열만 뽑아서 파싱하려는 보조 함수
    """
    raw = raw.strip()

    # ```json ... ``` 제거
    if raw.startswith("```"):
        # ```json\n ... \n```
        m = re.search(r"```(?:json)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
        if m:
            raw = m.group(1).strip()

    # 대충이라도 첫 [ ~ 마지막 ] 사이를 잡아서 본다
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        raw_candidate = raw[start : end + 1]
    else:
        raw_candidate = raw

    try:
        data = json.loads(raw_candidate)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    return []


def _extract_json_object(raw: str):
    """
    단일 JSON 객체를 파싱하기 위한 보조 함수
    (```json { ... } ``` 같이 줘도 robust 하게 처리)
    """
    raw = raw.strip()

    if raw.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
        if m:
            raw = m.group(1).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw_candidate = raw[start : end + 1]
    else:
        raw_candidate = raw

    try:
        data = json.loads(raw_candidate)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


# ======================
# 🤖 OpenAI 클라이언트
# ======================
class OpenAIClient:
    def chat(
        self,
        model: str,
        messages: list,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 1.0,
    ):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        try:
            r = requests.post(
                url,
                headers=_headers_openai(),
                json=payload,
                timeout=CHAT_TIMEOUT,
            )
        except requests.Timeout:
            raise RuntimeError("OpenAI Chat Timeout")

        if r.status_code >= 400:
            raise RuntimeError(f"[CHAT ERR {r.status_code}] {r.text}")

        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

    # Vision OCR
    def vision_to_text(
        self,
        model: str,
        image_b64: str,
        prompt: str = "Extract Korean text",
        mime: str = "image/png",
    ):
        url = f"{OPENAI_BASE_URL}/chat/completions"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}",
                        },
                    },
                ],
            }
        ]
        payload = {"model": model, "messages": messages}

        try:
            r = requests.post(
                url,
                headers=_headers_openai(),
                json=payload,
                timeout=VISION_TIMEOUT,
            )
        except requests.Timeout:
            raise RuntimeError("Vision OCR Timeout")

        if r.status_code >= 400:
            raise RuntimeError(f"[VISION ERR {r.status_code}] {r.text}")

        data = r.json()
        return data["choices"][0]["message"]["content"].strip()


# 전역 인스턴스
client = OpenAIClient()


# ======================================================
# 🔥 난이도별 요약 생성
# ======================================================
def generate_summary(text: str, difficulty: str):
    difficulty_prompts = {
        "ELEMENTARY": (
            "초등학생도 이해할 수 있게 매우 쉽게, 짧은 문장으로 설명해줘. "
            "어려운 단어는 피하고 핵심만 부드럽게 정리해."
        ),
        "SECONDARY": (
            "중학생과 고등학생이 이해할 수 있도록 알기 쉽게 정리해줘. "
            "기본 개념은 포함하고 너무 어렵지 않게."
        ),
        "ADULT": (
            "성인이 자연스럽게 읽을 수 있는 형태로 핵심을 명확하게 요약해줘."
        ),
    }

    prompt = difficulty_prompts.get(difficulty, difficulty_prompts["ADULT"])

    messages = [
        {"role": "system", "content": "You are a Korean summarizer."},
        {"role": "user", "content": f"{prompt}\n\n원문:\n{text}"},
    ]

    out = client.chat(SUMMARY_MODEL, messages, max_tokens=300)
    return out.strip()


# ======================================================
# 📚 어휘(어려운 단어) 추출 + 쉬운 설명
# ======================================================
def extract_vocabulary_explained(summary: str, difficulty: str):
    """
    요약문을 기반으로, 난이도 기준으로 어려울 수 있는 단어 3~10개를 골라
    - word
    - meaning (일반적인 뜻)
    - easy_meaning (경계선 지능/초등 수준에서도 이해 가능한 쉬운 설명)
    - example (간단 예문)
    형식으로 반환.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "너는 한국어 텍스트에서 어려운 단어를 뽑아서 아주 쉽게 설명해주는 도우미야. "
                "출력은 반드시 JSON 배열 형식만 사용해.\n\n"
                '형식 예시:\n'
                '[\n'
                '  {"word": "자본시장법", "meaning": "자본 시장을 규율하는 법률", '
                '"easy_meaning": "주식과 투자 관련 규칙을 정한 법", '
                '"example": "자본시장법을 어기면 처벌을 받을 수 있습니다."}\n'
                ']\n\n'
                "반드시 위와 같은 형태의 JSON 배열만 출력하고, 다른 설명 문장은 쓰지 마."
            ),
        },
        {
            "role": "user",
            "content": (
                f"난이도: {difficulty}\n"
                "아래 요약문에서, 이 난이도에서 이해하기 어려울 수 있는 단어 또는 표현을 3~10개 골라줘.\n"
                "특히 법률 용어, 경제 용어, 추상적인 단어를 우선적으로 선택해.\n"
                "각 항목은 다음 키를 포함해야 해:\n"
                "- word: 어려운 단어\n"
                "- meaning: 일반적인 뜻 (한두 문장)\n"
                "- easy_meaning: 초등학생도 이해할 수 있는 정말 쉬운 설명 (한두 문장)\n"
                "- example: 간단한 예문 (한국어)\n\n"
                "요약문:\n"
                f"{summary}"
            ),
        },
    ]

    raw = client.chat(SUMMARY_MODEL, messages, max_tokens=700)
    arr = _extract_json_array(raw)

    result = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word", "")).strip()
        if not word:
            continue
        meaning = str(item.get("meaning", "")).strip()
        easy_meaning = str(item.get("easy_meaning", "")).strip() or meaning
        example = str(item.get("example", "")).strip()

        result.append(
            {
                "word": word,
                "meaning": meaning,
                "easy_meaning": easy_meaning,
                "example": example,
            }
        )

    return result


# ======================================================
# 🔍 단어 하나를 더 자세하게, 쉽게 설명
# ======================================================
def explain_word_meaning(word: str, difficulty: str):
    """
    단어 하나를 선택했을 때, 추가로 더 쉽게 설명을 요청하는 용도.
    SummarizeAPI의 explain_word API 에서 사용.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "너는 한국어 어려운 단어를 초등학생도 이해할 수 있게 풀어서 설명해주는 선생님이야. "
                "JSON 객체 하나만 반환해야 해.\n\n"
                "형식:\n"
                '{\n'
                '  "word": "단어",\n'
                '  "meaning": "일반적인 뜻",\n'
                '  "easy_meaning": "아주 쉬운 설명",\n'
                '  "example": "간단한 예문"\n'
                "}\n"
                "절대로 다른 설명 문장을 붙이지 말고, 위 JSON 하나만 출력해."
            ),
        },
        {
            "role": "user",
            "content": (
                f"난이도: {difficulty}\n"
                f"아래 단어를 설명해줘.\n\n단어: {word}"
            ),
        },
    ]

    raw = client.chat(SUMMARY_MODEL, messages, max_tokens=300)
    obj = _extract_json_object(raw)

    # 기본값 처리
    result = {
        "word": word,
        "meaning": str(obj.get("meaning", "")).strip(),
        "easy_meaning": str(obj.get("easy_meaning", "")).strip()
        or str(obj.get("meaning", "")).strip(),
        "example": str(obj.get("example", "")).strip(),
    }
    return result


# ======================================================
# 🔍 문서 타입 자동 추론
# ======================================================
def detect_doc_type(summary: str):
    messages = [
        {"role": "system", "content": "문서 유형을 한 단어로 추론해라."},
        {
            "role": "user",
            "content": (
                "아래 요약을 읽고 문서 유형을 한국어 한 단어로만 추측해라.\n"
                f"{summary}"
            ),
        },
    ]
    result = client.chat(SUMMARY_MODEL, messages, max_tokens=20)
    return result.strip().split()[0]


# ======================================================
# 🔧 액션 아이템 추출
# ======================================================
def extract_actions(summary: str):
    messages = [
        {
            "role": "system",
            "content": (
                "너는 한국어 문서를 기반으로 '할 일 목록'만 추출하는 분석기다. "
                "출력은 반드시 JSON 배열만 반환해라."
            ),
        },
        {
            "role": "user",
            "content": (
                "아래 요약 내용을 기반으로 해야 할 행동(할 일)만 3~10개 추출해줘.\n"
                "문장은 '~하기' 형태만 사용.\n"
                "출력은 JSON 배열만:\n\n"
                f"{summary}"
            ),
        },
    ]

    out = client.chat(SUMMARY_MODEL, messages, max_tokens=300)
    arr = _extract_json_array(out)

    # 단순 문자열 리스트여도 허용
    if all(isinstance(x, str) for x in arr):
        return arr

    # [{ "todo": "..." }] 형태면 todo만 뽑기
    actions = []
    for item in arr:
        if isinstance(item, str):
            actions.append(item)
        elif isinstance(item, dict):
            v = item.get("todo") or item.get("action") or item.get("title")
            if isinstance(v, str):
                actions.append(v)

    return actions
# 맨 아래 적당한 곳에 추가하면 됨

def openai_chat_response(
    messages: list,
    model: str = SUMMARY_MODEL,
    max_tokens: int = 512,
    temperature: float = 0.2,
    top_p: float = 1.0,
) -> str:
    """
    예전 코드 호환용 helper.
    Roleplay 등에서 쓰는 openai_chat_response를
    새 client.chat 래핑해서 그대로 제공.
    """
    return client.chat(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
