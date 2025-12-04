import json
from django.urls import reverse
from django.core.management import call_command
import pytest

@pytest.mark.django_db
def test_next_and_submit(client):
    call_command("seed_quizzes")
    # EASY 하나 가져오기
    resp = client.get("/api/quizzes/next", {"difficulty":"EASY"})
    assert resp.status_code == 200
    body = resp.json()
    quiz_id = body["id"]
    # 정답 옵션 찾기(테스트에서는 고정 데이터이므로 서버 셔플해도 탐색)
    correct_opt = None
    for o in body["options"]:
        # seed에서 pk 끝이 1인 게 정답이었음
        if str(o["id"]).endswith("11"):
            correct_opt = o["id"]
            break
    assert correct_opt
    resp2 = client.post("/api/quizzes/submit", data={"quiz_id":quiz_id, "option_id":correct_opt, "time_ms":1500}, content_type="application/json")
    assert resp2.status_code == 200
    assert resp2.json()["correct"] is True
