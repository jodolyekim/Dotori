import os
import requests
import time


SIGHTENGINE_USER = os.environ.get("SIGHTENGINE_API_USER")
SIGHTENGINE_SECRET = os.environ.get("SIGHTENGINE_API_SECRET")

BASE_URL = "https://api.sightengine.com/1.0"


class SightEngineClient:
    @staticmethod
    def detect_image(file_obj):
        """
        Sightengine 이미지 AI 감지 (genai 모델)
        """
        url = f"{BASE_URL}/check.json"

        files = {"media": (file_obj.name, file_obj.read())}
        data = {
            "models": "genai",
            "api_user": SIGHTENGINE_USER,
            "api_secret": SIGHTENGINE_SECRET,
        }

        res = requests.post(url, files=files, data=data)
        res.raise_for_status()

        return res.json()

    @staticmethod
    def detect_video(file_obj):
        """
        Sightengine 비디오 Job 생성
        """
        url = f"{BASE_URL}/video/check.json"

        files = {"media": (file_obj.name, file_obj.read())}
        data = {
            "models": "genai",
            "api_user": SIGHTENGINE_USER,
            "api_secret": SIGHTENGINE_SECRET,
        }

        res = requests.post(url, files=files, data=data)
        res.raise_for_status()
        return res.json()  # job_id 포함

    @staticmethod
    def poll_video(job_id, timeout=20, interval=2):
        """
        Sightengine 비디오 결과 polling
        """
        url = f"{BASE_URL}/video/status.json"

        params = {
            "job_id": job_id,
            "api_user": SIGHTENGINE_USER,
            "api_secret": SIGHTENGINE_SECRET,
        }

        elapsed = 0
        while elapsed < timeout:
            res = requests.get(url, params=params)
            res.raise_for_status()
            data = res.json()

            if data.get("status") == "finished":
                return data

            time.sleep(interval)
            elapsed += interval

        return {"error": "video polling timeout", "job_id": job_id}
