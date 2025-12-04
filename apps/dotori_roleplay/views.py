# apps/dotori_roleplay/views.py
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .scenarios import get_scenario_or_none, list_scenarios
from apps.dotori_summaries.utils_openai import (
    openai_chat_response,
    SUMMARY_MODEL,
)
from apps.dotori_memberships.models_analytics import RoleplayLog  # 🔥 분석용 로그 모델


def _build_system_prompt(scenario) -> str:
    return f"""
너는 발달장애인 및 사회초보 사용자가 실제 일상 속 대화 상황을 연습하도록 돕는 
“역할극 전문 AI 코치 + 상대역 배우”이다.
항상 한국어·존댓말로만 말한다.

────────────────────────
📌 [역할 설정 – 매우 중요]
- 사용자는 시나리오 속 ‘나’(손님, 친구, 학생 등)를 연기한다.
- 너는 시나리오 속 ‘상대방’을 전문 배우처럼 연기하며 자연스럽게 반응한다.

assistant_reply를 생성할 때는 다음을 반드시 지켜라:
1) **시나리오의 상황·맥락과 직접적으로 관련된 대사만 생성한다.**
   - 상황과 무관한 대사(예: “괜찮으세요?”, “힘내세요”) 절대 금지.
   - ‘편의점 직원’이라면 직원다운 말만, ‘친구’라면 친구다운 말만 사용한다.

2) **맥락 기반 자연스러움 우선**
   - 사용자의 마지막 발화를 이해하고, 그 말에 대해 실제 인간처럼 대답한다.
   - 감정·배경·관계에 따라 말투를 미세하게 조정한다.

3) **사용자가 먼저 해야 할 말을 대신해도 된다.**
   단, **시나리오와 직접적으로 연관된 ‘의미 있는 말’이어야 한다.**
   (불필요하게 엉뚱한 제안 금지)

4) assistant_reply는
   - 설명, 조언, 예시 문장, 코칭 문장 제외
   - 현실적 대사 1~3문장만

────────────────────────
📌 [코칭 규칙]

coach_comment:
- 사용자의 발화를 평가하되 “1문장”만
- 진짜 대화 상황처럼 맥락에 맞는 피드백을 준다.

suggested_next_action:
- 현재 시나리오 + 사용자의 마지막 발화 + assistant_reply를 기반으로 **직접 이어질 수 있는 한 문장**만 제안
- 시나리오와 무관한 제안 절대 금지

────────────────────────
📌 [시나리오 정보]
제목: {scenario.title}
상황 설명: {scenario.description}
연습 목표: {scenario.goal}
태그: {", ".join(scenario.tags)}

이 내용을 기반으로, 상황을 매우 정확히 이해하고 유지해야 한다.

────────────────────────
📌 [출력 형식 – 반드시 지켜라]
아래 JSON 외 그 어떤 텍스트도 출력하지 마라.

{{
  "assistant_reply": "<상대방의 실제 대사>",
  "coach_comment": "<1문장 코칭>",
  "suggested_next_action": "<사용자가 다음에 말할 수 있는 한 문장>"
}}
"""



class RoleplayScenarioListView(APIView):
    """
    시나리오 목록 조회용
    """
    permission_classes = [AllowAny]  # 로그인 없이도 목록은 볼 수 있게 유지

    def get(self, request):
        scenarios = list_scenarios()
        data = [
            {
                "code": s.code,
                "title": s.title,
                "description": s.description,
                "goal": s.goal,
                "tags": s.tags,
            }
            for s in scenarios
        ]
        return Response(data)


class RoleplayChatView(APIView):
    """
    POST /api/roleplay/chat/
    body:
      - scenario_code: str
      - messages: [{ "role": "user" | "assistant", "content": "..." }, ...]
    response:
      - scenario_code
      - assistant_reply
      - coach_comment
      - suggested_next_action
    """
    permission_classes = [AllowAny]  # 🔥 비로그인도 사용 가능하되, 로그는 로그인 유저만

    def post(self, request):
        scenario_code = request.data.get("scenario_code")
        raw_messages = request.data.get("messages") or []

        scenario = get_scenario_or_none(str(scenario_code or ""))
        if not scenario:
            return Response(
                {"detail": f"Invalid scenario_code: {scenario_code}"},
                status=400,
            )

        # history 정제
        history: list[dict] = []
        for m in raw_messages:
            role = m.get("role")
            content = m.get("content")
            if role not in ("user", "assistant"):
                continue
            if not content:
                continue
            history.append({"role": role, "content": str(content)})

        # system 프롬프트 + history
        system_prompt = _build_system_prompt(scenario)
        messages = [{"role": "system", "content": system_prompt}] + history

        # OpenAI 호출
        try:
            raw = openai_chat_response(
                messages,
                model=SUMMARY_MODEL,
                max_tokens=512,
            )
        except Exception as e:
            return Response(
                {"detail": f"OpenAI 호출 실패: {e}"},
                status=500,
            )

        assistant_reply = ""
        coach_comment = ""
        suggested_next_action = ""

        # 모델이 JSON으로 잘 줬다고 가정하고 파싱 시도
        try:
            parsed = json.loads(raw)
            assistant_reply = str(parsed.get("assistant_reply") or "").strip()
            coach_comment = str(parsed.get("coach_comment") or "").strip()
            suggested_next_action = str(parsed.get("suggested_next_action") or "").strip()
        except Exception:
            # JSON 파싱 실패하면, 전체 답변을 assistant_reply 로만 사용
            assistant_reply = raw.strip()

        if not assistant_reply:
            assistant_reply = "죄송해요, 이번에는 적절한 답변을 만들지 못했어요. 다시 한 번 말씀해 주실래요?"

        # 🔥 롤플레잉 사용 로그 저장 (로그인 유저만)
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if request.user.is_authenticated:
            # history 중 마지막 user 발화 찾아 길이 측정
            last_user_content = ""
            for m in reversed(history):
                if m["role"] == "user":
                    last_user_content = m["content"]
                    break
            utter_len = len(last_user_content or "")

            try:
                RoleplayLog.objects.create(
                    user=request.user,
                    scenario_code=scenario.code,
                    user_utterance_len=utter_len,
                )
                print(
                    f"[RoleplayLog] created: user={request.user.id}, "
                    f"scenario={scenario.code}, len={utter_len}, "
                    f"Authorization='{auth_header}'",
                    flush=True,
                )
            except Exception as e:
                # 로그 실패해도 서비스 동작에는 영향 없게
                print(
                    f"[RoleplayLog] create 실패: {e}. Authorization='{auth_header}'",
                    flush=True,
                )
        else:
            print(
                f"[RoleplayLog] skip: unauthenticated user. Authorization='{auth_header}'",
                flush=True,
            )

        resp = {
            "scenario_code": scenario.code,
            "assistant_reply": assistant_reply,
            "coach_comment": coach_comment,
            "suggested_next_action": suggested_next_action,
        }
        return Response(resp)
