"""
鉴权模块：密码哈希 + JWT(HS256)。

刻意只用 Python 标准库实现，不引第三方 JWT 包——教程里可以把签名原理逐步拆开讲，
也避免 CI 里多一个依赖。生产部署必须通过环境变量 JWT_SECRET 覆盖默认开发密钥。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, Header, HTTPException

from . import config, db

_PBKDF2_ROUNDS = 120_000


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------- 密码 ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                   bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(calc.hex(), digest_hex)
    except Exception:
        return False


# ---------- JWT HS256 ----------
def make_token(user: dict) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps({
        "uid": user["id"], "sub": user["username"], "role": user["role"],
        "iat": int(time.time()), "exp": int(time.time()) + config.JWT_TTL,
    }, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = _b64url(hmac.new(config.JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def parse_token(token: str) -> dict[str, Any]:
    try:
        header, payload, sig = token.split(".")
        expected = _b64url(hmac.new(config.JWT_SECRET.encode(),
                                    f"{header}.{payload}".encode("ascii"),
                                    hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = json.loads(_b64url_decode(payload))
        if int(data.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return data
    except Exception:
        raise HTTPException(401, "Unauthorized")


# ---------- FastAPI 依赖 ----------
def current_user(authorization: str | None = Header(default=None)) -> dict:
    """从 Authorization: Bearer <token> 解析当前用户；缺失/无效一律 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")
    data = parse_token(authorization[7:].strip())
    user = db.get_user_by_id(int(data["uid"]))
    if not user:
        raise HTTPException(401, "Unauthorized")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "ADMIN":
        raise HTTPException(403, "需要管理员权限")
    return user
