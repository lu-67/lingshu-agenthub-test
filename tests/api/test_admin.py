"""
管理后台模块用例（6 个接口）
============================
覆盖：用户列表（普通用户 403 / admin 200）、平台统计、
单个用户详情、删除不存在用户 404、数据库状态、调度器状态、
删除自己被 400 拒绝。
"""
from __future__ import annotations

import pytest


# ── 普通用户一律 403 ────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/admin/users",
    "/api/admin/stats",
    "/api/admin/db/overview",
    "/api/admin/scheduler/status",
])
def test_admin_endpoints_forbidden_for_normal_user(api, path: str):
    resp = api.get(path)
    assert resp.status_code == 403, f"普通用户调 {path} 应被 403"


def test_admin_user_detail_forbidden_for_normal_user(api):
    resp = api.get("/api/admin/users/1")
    assert resp.status_code == 403


def test_admin_delete_forbidden_for_normal_user(api):
    resp = api.delete("/api/admin/users/999")
    assert resp.status_code == 403


# ── 无 token 一律 401 ───────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/admin/users",
    "/api/admin/stats",
    "/api/admin/users/1",
    "/api/admin/users/999",
    "/api/admin/db/overview",
    "/api/admin/scheduler/status",
])
def test_admin_endpoints_without_token(base_url, path: str):
    import requests
    method = "DELETE" if path.endswith("999") else "GET"
    resp = requests.request(method, f"{base_url}{path}", timeout=10)
    assert resp.status_code == 401


# ── admin 正常访问 ──────────────────────────────────────

def test_admin_users_list(admin):
    resp = admin.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("users"), list)
    names = {u["username"] for u in data["users"]}
    assert "admin" in names
    for u in data["users"]:
        assert "password" not in u and "password_hash" not in u


def test_admin_stats(admin):
    resp = admin.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data and data["users"] >= 1


def test_admin_user_detail_tester(admin):
    # 动态找 tester 的 uid
    users = admin.get("/api/admin/users").json()["users"]
    tester_uid = next((u["id"] for u in users if u["username"] == "tester"), None)
    if not tester_uid:
        pytest.skip("tester 账号不存在")
    resp = admin.get(f"/api/admin/users/{tester_uid}")
    assert resp.status_code == 200
    assert resp.json().get("username") == "tester"


def test_admin_user_detail_not_found(admin):
    resp = admin.get("/api/admin/users/99999")
    assert resp.status_code == 404


def test_admin_delete_nonexistent_user(admin):
    """BUG-009 修复：不存在的 uid 必须 404。"""
    resp = admin.delete("/api/admin/users/99999")
    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


def test_admin_delete_self_forbidden(admin):
    """admin 不能删自己。"""
    my_id = admin.get("/api/auth/me").json()["id"]
    resp = admin.delete(f"/api/admin/users/{my_id}")
    assert resp.status_code == 400
    assert "不能删除自己" in resp.json()["detail"]


def test_admin_db_overview(admin):
    resp = admin.get("/api/admin/db/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("backend") in ("mysql", "sqlite")  # 字段名是 backend
    assert isinstance(data.get("tables"), dict) or "tables" in data


def test_admin_scheduler_status(admin):
    resp = admin.get("/api/admin/scheduler/status")
    assert resp.status_code == 200
    assert "jobs" in resp.json()
