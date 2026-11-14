"""Redis 会话记忆 + 执行结果缓存。Redis 不可用时自动降级为内存实现，服务不中断。"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import config

_redis = None
_local: dict[str, tuple[str, float]] = {}
_history_local: dict[str, list[dict[str, str]]] = {}


def client():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis
        c = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT,
                        db=config.REDIS_DB, password=config.REDIS_PASSWORD,
                        socket_connect_timeout=1, socket_timeout=1, decode_responses=True,
                        # 部分 Windows Redis / 兼容实现不支持 RESP3 的 HELLO 握手，强制 RESP2
                        protocol=2)
        c.ping()
        _redis = c
        return c
    except Exception:
        return None


def available() -> bool:
    return client() is not None


def cache_key(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return "nexus:run:" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_cached(key: str) -> dict[str, Any] | None:
    c = client()
    try:
        if c:
            v = c.get(key)
            return json.loads(v) if v else None
        import time
        item = _local.get(key)
        if item and item[1] > time.time():
            return json.loads(item[0])
    except Exception:
        pass
    return None


def set_cached(key: str, value: dict[str, Any]) -> None:
    c = client()
    raw = json.dumps(value, ensure_ascii=False)
    try:
        if c:
            c.setex(key, config.CACHE_TTL, raw)
        else:
            import time
            _local[key] = (raw, time.time() + config.CACHE_TTL)
    except Exception:
        pass


def history_key(conversation_id: int | None) -> str:
    return f"nexus:history:{conversation_id or 0}"


def get_history(conversation_id: int | None) -> list[dict[str, str]]:
    if conversation_id is None:
        return []
    key = history_key(conversation_id)
    c = client()
    try:
        if c:
            raw = c.lrange(key, -20, -1)
            return [json.loads(x) for x in raw]
        return list(_history_local.get(key, []))
    except Exception:
        return []


def append_history(conversation_id: int | None, user_msg: str, answer: str) -> None:
    if conversation_id is None:
        return
    key = history_key(conversation_id)
    items = [{"role": "user", "content": user_msg}, {"role": "assistant", "content": answer}]
    c = client()
    try:
        if c:
            pipe = c.pipeline()
            for it in items:
                pipe.rpush(key, json.dumps(it, ensure_ascii=False))
            pipe.ltrim(key, -20, -1)
            pipe.expire(key, 3600)
            pipe.execute()
        else:
            _history_local.setdefault(key, []).extend(items)
            del _history_local[key][:-20]
    except Exception:
        pass
