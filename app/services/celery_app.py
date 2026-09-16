import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def normalize_celery_redis_url(redis_url: str) -> str:
    """Add the TLS option required by Celery for rediss:// Redis URLs."""
    if not redis_url.startswith("rediss://"):
        return redis_url

    parts = urlsplit(redis_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("ssl_cert_reqs", "CERT_REQUIRED")
    return urlunsplit(parts._replace(query=urlencode(query)))


redis_url = normalize_celery_redis_url(
    os.getenv("REDIS_URL")
    or os.getenv("UPSTASH_REDIS_URL", "redis://localhost:6379/0")
)

celery_app = Celery(
    "ai-knowledge-agent",
    broker=normalize_celery_redis_url(os.getenv("CELERY_BROKER_URL", redis_url)),
    backend=normalize_celery_redis_url(os.getenv("CELERY_RESULT_BACKEND", redis_url)),
    include=["app.services.document_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)