import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL") or os.getenv(
    "UPSTASH_REDIS_URL", "redis://localhost:6379/0"
)

celery_app = Celery(
    "ai-knowledge-agent",
    broker=os.getenv("CELERY_BROKER_URL", redis_url),
    backend=os.getenv("CELERY_RESULT_BACKEND", redis_url),
    include=["app.services.document_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)