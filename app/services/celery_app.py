import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from celery import Celery
except ImportError:  # pragma: no cover - optional local dependency
    class Celery:
        def __init__(self, *args, **kwargs):
            self.tasks = {}

        def task(self, *args, **kwargs):
            def decorator(func):
                self.tasks[func.__name__] = func
                return func
            return decorator

        def conf(self):
            return {}

        def config_from_object(self, *args, **kwargs):
            return None

        def update(self, *args, **kwargs):
            return None

    Celery = None

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
broker_url = normalize_celery_redis_url(os.getenv("CELERY_BROKER_URL", redis_url))
backend_url = normalize_celery_redis_url(os.getenv("CELERY_RESULT_BACKEND", redis_url))

redis_ssl_options = {
    "ssl_cert_reqs": ssl.CERT_REQUIRED,
}
tls_config = {}
if broker_url.startswith("rediss://"):
    tls_config["broker_use_ssl"] = redis_ssl_options
if backend_url.startswith("rediss://"):
    tls_config["redis_backend_use_ssl"] = redis_ssl_options

if Celery is None:
    celery_app = None
else:
    celery_app = Celery(
        "ai-knowledge-agent",
        broker=broker_url,
        backend=backend_url,
        include=["app.services.document_tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_track_started=True,
        **tls_config,
    )