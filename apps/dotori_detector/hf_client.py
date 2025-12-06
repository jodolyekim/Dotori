'''
# apps/dotori_detector/hf_client.py
import os, json, base64, requests, uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

HF_API_KEY = os.getenv("HF_API_KEY", "").strip()

def _auth_header():
    if not HF_API_KEY:
        raise RuntimeError("HF_API_KEY is not set")
    return {"Authorization": f"Bearer {HF_API_KEY}"}

def hf_binary_infer(url: str, blob: bytes, timeout: int = 60) -> dict:
    """
    허깅페이스 Inference API에 대해 전송형식 3종을 자동 재시도:
      1) application/octet-stream  (표준 이미지/오디오 바이너리)
      2) application/json          (inputs: base64)
      3) multipart/form-data       (file=@...)
    실패하면 마지막 오류 본문/상태코드를 포함한 dict 반환
    """
    if not url:
        raise RuntimeError("HF url is empty")

    h_auth = _auth_header()

    # 1) octet-stream
    try:
        r = requests.post(
            url,
            headers={**h_auth, "Accept": "application/json", "Content-Type": "application/octet-stream"},
            data=blob,
            timeout=timeout,
        )
        if r.status_code < 400:
            return _safe_json(r)
        err1 = _errpack(r)
    except Exception as e:
        err1 = {"error": f"octet-stream failed: {e}"}

    # 2) json (base64)
    try:
        b64 = base64.b64encode(blob).decode("ascii")
        payload = {"inputs": b64}
        r = requests.post(
            url,
            headers={**h_auth, "Accept": "application/json", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=timeout,
        )
        if r.status_code < 400:
            return _safe_json(r)
        err2 = _errpack(r)
    except Exception as e:
        err2 = {"error": f"json(base64) failed: {e}"}

    # 3) multipart/form-data
    try:
        boundary = f"HFForm{uuid.uuid4().hex}"
        files = {"file": ("upload.bin", blob, "application/octet-stream")}
        r = requests.post(url, headers=h_auth, files=files, timeout=timeout)
        if r.status_code < 400:
            return _safe_json(r)
        err3 = _errpack(r)
    except Exception as e:
        err3 = {"error": f"multipart failed: {e}"}

    return {"error": "all attempts failed", "octet": err1, "json": err2, "multipart": err3}

def _safe_json(r: requests.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {"ok": True, "raw_len": len(r.content), "content_type": r.headers.get("content-type", "")}

def _errpack(r: requests.Response) -> dict:
    try:
        body = r.json()
    except Exception:
        body = {"text": r.text[:500]}
    return {"status": r.status_code, "body": body}

def _label_to_ai_flag(label: str) -> float | None:
    """
    다양한 라벨 문자열을 확률(0~1)로 매핑. 확률이 없을 땐 휴리스틱.
    """
    if not isinstance(label, str):
        return None
    l = label.strip().lower()
    if l in {"ai","fake","synthetic","generated","deepfake"}:
        return 0.9
    if l in {"human","real","authentic","genuine"}:
        return 0.1
    return None

def pick_score_label(raw: dict, default_score: float = 0.5):
    """
    HF 응답의 다양한 형태를 유연하게 파싱하여 (score, label)로 통일
    허용 형태 예:
      - {"score": 0.73, "label": "fake"}
      - {"predictions": [{"score": 0.73, "label": "fake"}, ...]}
      - {"results": [...]} / {"outputs": [...]}
      - {"logits": [..]}  (softmax 0번을 ai로 가정)
      - {"is_ai": true} / {"is_fake": true} 등
    """
    if not isinstance(raw, dict):
        return default_score, "unknown"

    # 1) 직접 score/label
    score = raw.get("score", None)
    label = raw.get("label", None)
    if isinstance(score, (int, float)):
        return float(score), (str(label).lower() if isinstance(label, str) else "unknown")
    if isinstance(label, str):
        flag = _label_to_ai_flag(label)
        if flag is not None:
            return float(flag), label.lower()

    # 2) predictions/results/outputs 리스트
    for key in ("predictions", "results", "outputs"):
        preds = raw.get(key)
        if isinstance(preds, list) and preds:
            item = preds[0]
            if isinstance(item, dict):
                s = item.get("score")
                l = item.get("label")
                if isinstance(s, (int, float)):
                    return float(s), (str(l).lower() if isinstance(l, str) else "unknown")
                if isinstance(l, str):
                    flag = _label_to_ai_flag(l)
                    if flag is not None:
                        return float(flag), l.lower()

    # 3) is_ai / is_fake 류 불리언
    for key in ("is_ai", "is_fake", "ai", "fake"):
        v = raw.get(key)
        if isinstance(v, bool):
            return (0.9 if v else 0.1), ("ai" if v else "human")

    # 4) logits
    logits = raw.get("logits")
    if isinstance(logits, list) and logits:
        try:
            import math
            exps = [math.exp(float(x)) for x in logits]
            smax = [e / sum(exps) for e in exps]
            ai_prob = float(smax[0])  # 0번을 ai로 가정
            return ai_prob, ("ai" if ai_prob >= 0.5 else "human")
        except Exception:
            pass

    return default_score, "unknown"
'''