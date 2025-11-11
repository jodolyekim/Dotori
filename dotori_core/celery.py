import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dotori_core.settings')
app = Celery('dotori_core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
