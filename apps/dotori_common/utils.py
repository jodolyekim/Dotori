# apps/dotori_common/utils.py
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    # CoolSMS Python SDK
    # pip install coolsms_python_sdk
    from sdk.api.message import Message
    from sdk.exceptions import CoolsmsException
except Exception:  # ImportError 등
    Message = None
    CoolsmsException = Exception


@dataclass
class ApiResponse:
    ok: bool
    message: Optional[str] = None
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"ok": self.ok}
        if self.message:
            out["message"] = self.message
        if self.data is not None:
            out["data"] = self.data
        return out


def send_sms_verification_code(phone: str, code: str) -> ApiResponse:
    """
    CoolSMS를 이용해 인증번호 SMS를 발송한다.

    설정 읽는 우선순위:
    1) Django settings.COOlSMS_*
    2) 환경변수 COOLSMS_*

    필요한 값:
    - COOLSMS_API_KEY
    - COOLSMS_API_SECRET
    - COOLSMS_SENDER_NUMBER
    """
    api_key = getattr(settings, "COOLSMS_API_KEY", None) or os.getenv("COOLSMS_API_KEY")
    api_secret = getattr(settings, "COOLSMS_API_SECRET", None) or os.getenv("COOLSMS_API_SECRET")
    sender = getattr(settings, "COOLSMS_SENDER_NUMBER", None) or os.getenv("COOLSMS_SENDER_NUMBER")

    if not api_key or not api_secret or not sender:
        msg = "CoolSMS 설정(키/시크릿/발신번호)이 없습니다. COOLSMS_API_KEY / COOLSMS_API_SECRET / COOLSMS_SENDER_NUMBER 를 확인해주세요."
        logger.error("[CoolSMS] %s", msg)
        return ApiResponse(False, msg)

    if Message is None:
        msg = "CoolSMS Python SDK가 설치되어 있지 않습니다. (pip install coolsms_python_sdk)"
        logger.error("[CoolSMS] %s", msg)
        return ApiResponse(False, msg)

    text = f"[도토리] 인증번호 {code} 를 입력해주세요."

    params: Dict[str, Any] = {
        "type": "sms",      # sms / lms / mms / ata 등
        "to": phone,        # 수신번호 (숫자만)
        "from": sender,     # CoolSMS에 등록된 발신번호
        "text": text,
    }

    try:
        cool = Message(api_key, api_secret)
        resp = cool.send(params)

        success = resp.get("success_count", 0)
        error = resp.get("error_count", 0)
        logger.info(
            "[CoolSMS] send result: success=%s error=%s group_id=%s",
            success,
            error,
            resp.get("group_id"),
        )

        if success > 0 and error == 0:
            return ApiResponse(True, "문자 발송 성공", data=resp)

        msg = f"문자 발송 실패: {resp}"
        logger.error("[CoolSMS] %s", msg)
        return ApiResponse(False, msg, data=resp)

    except CoolsmsException as e:  # type: ignore
        msg = f"CoolSMS 예외: code={getattr(e, 'code', None)} msg={getattr(e, 'msg', str(e))}"
        logger.error("[CoolSMS] %s", msg)
        return ApiResponse(False, msg)

    except Exception as e:
        msg = f"SMS 발송 중 알 수 없는 오류: {e}"
        logger.exception("[CoolSMS] %s", msg)
        return ApiResponse(False, msg)
