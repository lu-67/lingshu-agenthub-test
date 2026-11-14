"""
认证模块用例（captcha / register / login / me）
===============================================
覆盖：验证码格式校验、正常注册登录、参数校验、重复用户名、
错误密码、Token 缺失与伪造、admin 与普通用户角色区分。
"""
from __future__ import annotations

import uuid

import pytest
import requests

from conftest import BASE_URL


def _username() -> str:
    return f"case_{uuid.uuid4().hex[:8]}"


# ── captcha ──────────────────────────────────────────────

def test_captcha_returns_id_and_image():
    resp = requests.get(f"{BASE_URL}/api/captcha", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data and data["id"]
    assert "image" in data and data["image"].startswith("data:")


# ── register ─────────────────────────────────────────────

def test_register_success():
    username = _username()
    resp = requests.post(f"{BASE_URL}/api/auth/register",
                         json={"username": username, "password": "Case1234"}, timeout=30)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["username"] == username
    assert data["role"] == "USER"
    assert len(data["token"].split(".")) == 3  # JWT 三段


def test_register_duplicate_username(api):
    resp = requests.post(f"{BASE_URL}/api/auth/register",
                         json={"username": api.username, "password": "Case1234"}, timeout=30)
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]


@pytest.mark.parametrize("username, password, field", [
    ("ab", "Case1234", "用户名"),       # 太短
    ("abcde", "123", "密码"),           # 密码太短
])
def test_register_validation(username: str, password: str, field: str):
    resp = requests.post(f"{BASE_URL}/api/auth/register",
                         json={"username": username, "password": password}, timeout=30)
    assert resp.status_code == 400
    assert field in resp.json()["detail"]


# ── login ────────────────────────────────────────────────

def test_login_success(api):
    resp = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"username": api.username, "password": api.password},
                         timeout=30)
    assert resp.status_code == 200, resp.text
    assert resp.json()["token"]  # 有 token 就算过


def test_login_wrong_password(api):
    resp = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"username": api.username, "password": "wrong-pass"},
                         timeout=30)
    assert resp.status_code == 400


def test_login_unknown_user():
    resp = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"username": "no_such_user_9527", "password": "Case1234"},
                         timeout=30)
    assert resp.status_code == 400


# ── me ───────────────────────────────────────────────────

def test_me_returns_profile(api):
    resp = api.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == api.username
    assert data["role"] == "USER"
    assert "password" not in data and "password_hash" not in data


def test_me_without_token():
    resp = requests.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert resp.status_code == 401


def test_me_with_forged_token(api):
    forged = api.token[:-4] + "abcd"
    resp = requests.get(f"{BASE_URL}/api/auth/me",
                        headers={"Authorization": f"Bearer {forged}"}, timeout=30)
    assert resp.status_code == 401


def test_admin_account_role(admin):
    resp = admin.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"
