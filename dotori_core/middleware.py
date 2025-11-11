# dotori_core/middleware.py
from django.conf import settings

class AllowCORSForMedia:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        res = self.get_response(request)
        try:
            media_url = getattr(settings, "MEDIA_URL", "/media/")
            if request.path.startswith(media_url):
                # CORS: CanvasKit에서 이미지 로딩 시 필요
                res["Access-Control-Allow-Origin"] = "*"
                res["Access-Control-Expose-Headers"] = "Content-Type, Content-Length"
                # (필요시) 인증 쿠키를 쓰지 않으니 credentials는 생략
        except Exception:
            pass
        return res
