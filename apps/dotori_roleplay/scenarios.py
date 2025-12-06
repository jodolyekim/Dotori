# apps/dotori_roleplay/scenarios.py

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RoleplayScenario:
    code: str          # "friend_fell"
    title: str         # "친구가 넘어졌을 때"
    description: str   # 상황 설명
    goal: str          # 연습 목표 (공감, 도움 요청 등)
    tags: List[str]    # ["공감", "도움주기"]


SCENARIOS: Dict[str, RoleplayScenario] = {
    # 1) 기존 시나리오들 -
    "friend_fell": RoleplayScenario(
        code="friend_fell",
        title="친구가 넘어졌을 때",
        description=(
            "친구와 함께 걷다가 친구가 갑자기 넘어져서 무릎을 다친 상황입니다. "
            "친구는 당황하고 아파 보이지만, 당신은 뭐라고 말을 꺼내야 할지 고민하고 있습니다."
        ),
        goal="상대의 상태를 확인하고, 공감과 도움을 자연스럽게 표현하는 말을 연습합니다.",
        tags=["공감", "도움주기", "일상대화"],
    ),
    "comfort_sad_friend": RoleplayScenario(
        code="comfort_sad_friend",
        title="속상한 친구 위로하기",
        description=(
            "친구가 시험을 망치고 난 뒤 많이 속상해 합니다. "
            "본인은 농담도 하고 웃으려고 하지만, 속으로는 많이 힘들어 보입니다."
        ),
        goal="상대의 감정을 먼저 인정하고, 부담스럽지 않은 위로를 연습합니다.",
        tags=["공감", "위로", "감정인정"],
    ),
    "ask_staff_convenience_store": RoleplayScenario(
        code="ask_staff_convenience_store",
        title="편의점에서 물건 위치 물어보기",
        description=(
            "편의점에서 라면을 찾고 싶은데 어디 있는지 잘 모르겠습니다. "
            "직원은 계산대에 서 있고, 손님들이 왔다 갔다 하는 상황입니다."
        ),
        goal="상대에게 예의있게 부탁하고, 간단한 질문을 연습합니다.",
        tags=["질문하기", "일상생활", "부탁하기"],
    ),

    # 2) 새 시나리오들 -
    "school_group_presentation": RoleplayScenario(
        code="school_group_presentation",
        title="조별 과제에서 의견 말하기",
        description=(
            "수업 시간에 조별 발표를 준비하는 상황입니다. "
            "조원들이 발표 방식과 내용을 정하고 있는데, 당신도 아이디어가 있지만 "
            "말해도 될지, 어떻게 말해야 할지 망설이고 있습니다."
        ),
        goal="내 의견을 부드럽게 제안하고, 다른 사람의 의견을 존중하는 표현을 연습합니다.",
        tags=["학교", "의견나누기", "협력"],
    ),
    "ask_teacher_question": RoleplayScenario(
        code="ask_teacher_question",
        title="수업 시간에 모르는 내용 질문하기",
        description=(
            "수업을 듣다가 이해가 잘 되지 않는 부분이 있습니다. "
            "수업이 끝난 뒤 선생님께 다가가 조심스럽게 질문하려는 상황입니다."
        ),
        goal="모르는 내용을 인정하고, 예의 있게 질문하는 표현을 연습합니다.",
        tags=["학교", "질문하기", "소통"],
    ),
    "subway_seat": RoleplayScenario(
        code="subway_seat",
        title="지하철에서 자리 양보하기",
        description=(
            "지하철이 붐비는 상황에서, 앞에 어르신이나 힘들어 보이는 사람이 서 있습니다. "
            "당신은 앉아 있고, 자리를 양보하고 싶은데 어떻게 말을 꺼내야 할지 고민하고 있습니다."
        ),
        goal="상대에게 부담을 덜 주면서도 예의 있게 자리를 양보하는 표현을 연습합니다.",
        tags=["대중교통", "예의", "도움주기"],
    ),
    "noisy_neighbor": RoleplayScenario(
        code="noisy_neighbor",
        title="시끄러운 이웃에게 정중하게 말하기",
        description=(
            "오랫동안 윗집/옆집에서 발소리나 음악 소리가 크게 들려서 잠을 잘 자기 힘든 상황입니다. "
            "화가 나긴 하지만, 싸우지 않고 예의 있게 부탁하고 싶습니다."
        ),
        goal="감정을 폭발시키지 않고, 구체적으로 불편함을 설명하고 부탁하는 방법을 연습합니다.",
        tags=["주거", "갈등해결", "부탁하기"],
    ),
    "parttime_rude_customer": RoleplayScenario(
        code="parttime_rude_customer",
        title="알바 중 불친절한 손님 응대하기",
        description=(
            "편의점이나 카페 등에서 아르바이트 중, 실수로 인해 손님이 화를 내는 상황입니다. "
            "손님은 목소리가 점점 커지고 있고, 당신은 당황스러워 하고 있습니다."
        ),
        goal="사과와 설명을 적절히 섞어, 상황을 진정시키는 표현을 연습합니다.",
        tags=["알바", "서비스", "갈등해결"],
    ),
    "family_talk_stress": RoleplayScenario(
        code="family_talk_stress",
        title="부모님께 힘들다고 말하기",
        description=(
            "최근에 학교나 일, 인간관계 때문에 많이 지쳐 있습니다. "
            "부모님은 걱정하고 있지만, 당신은 솔직하게 말하기가 조금 부담스럽습니다."
        ),
        goal="내 상태를 차분하게 설명하고, 도움이나 이해를 요청하는 말을 연습합니다.",
        tags=["가족", "감정표현", "도움요청"],
    ),
    "groupchat_misunderstanding": RoleplayScenario(
        code="groupchat_misunderstanding",
        title="단체 채팅방에서 오해 풀기",
        description=(
            "단체 채팅방에서 당신이 한 말이 오해를 불러 일으켜 친구가 서운해 하는 상황입니다. "
            "직접 만나서 이야기하기로 했고, 어떻게 풀어야 할지 연습하려고 합니다."
        ),
        goal="상대의 감정을 인정하면서, 자신의 의도를 차분하게 설명하는 연습을 합니다.",
        tags=["친구", "갈등해결", "사과"],
    ),
}


def list_scenarios() -> List[RoleplayScenario]:
    return list(SCENARIOS.values())


def get_scenario_or_none(code: str) -> RoleplayScenario | None:
    return SCENARIOS.get(code)
