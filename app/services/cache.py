import hashlib
import json
import logging
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_redis_client = None


def get_cache_ttl() -> int:
    try:
        return max(1, int(os.getenv("REDIS_CACHE_TTL_SECONDS", "600")))
    except ValueError:
        logger.warning("Invalid REDIS_CACHE_TTL_SECONDS; using 600 seconds")
        return 600


def get_redis_client():
    """Return the shared Redis client, creating it lazily on first use."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL") or os.getenv(
            "UPSTASH_REDIS_URL", "redis://localhost:6379/0"
        )
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def response_cache_key(org_id: str, question: str, conversation_id: str | None) -> str:
    question_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()
    conversation_part = conversation_id or "new"
    return f"ai-knowledge:response:{org_id}:{conversation_part}:{question_hash}"


def conversation_cache_key(org_id: str, user_id: str, conversation_id: str) -> str:
    return f"ai-knowledge:conversation:{org_id}:{user_id}:{conversation_id}"


def get_cached(key: str) -> Any | None:
    try:
        value = get_redis_client().get(key)
        return json.loads(value) if value else None
    except (redis.RedisError, json.JSONDecodeError):
        logger.warning("Redis cache read failed for key %s", key, exc_info=True)
        return None


def set_cached(key: str, value: Any) -> None:
    try:
        get_redis_client().setex(
            key,
            get_cache_ttl(),
            json.dumps(value, default=str),
        )
    except (redis.RedisError, TypeError):
        logger.warning("Redis cache write failed for key %s", key, exc_info=True)


def delete_conversation_cached(conversation_id: str) -> None:
    try:
        client = get_redis_client()
        pattern = f"ai-knowledge:conversation:*:*:{conversation_id}"
        keys = list(client.scan_iter(match=pattern))
        if keys:
            client.delete(*keys)
    except redis.RedisError:
        logger.warning(
            "Redis conversation cache invalidation failed for %s",
            conversation_id,
            exc_info=True,
        )