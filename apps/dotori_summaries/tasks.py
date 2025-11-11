from celery import shared_task
from .models import Summary
@shared_task
def run_summary(summary_id: int):
    obj = Summary.objects.get(id=summary_id)
    try:
        text = obj.source_text.strip()
        if not text:
            obj.status = "ERROR"
            obj.result = "빈 텍스트"
            obj.save(); return
        import re
        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        draft = " ".join(sentences[:3])[:300]
        obj.result = draft if draft else text[:300]
        obj.status = "DONE"
        obj.save()
    except Exception as e:
        obj.status = "ERROR"
        obj.result = str(e)
        obj.save()
