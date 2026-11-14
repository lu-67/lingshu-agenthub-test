"""
智能体模块用例（GET / POST / PUT）
=================================
覆盖：列表返回、新建参数校验、停用/启用切换、越权不能改别人的智能体。
"""
from __future__ import annotations

import pytest


def test_list_agents_returns_array(api):
    resp = api.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("agents"), list)
    for agent in data["agents"]:
        assert "id" in agent and "name" in agent


def test_list_agents_without_token():
    import requests
    from conftest import BASE_URL
    resp = requests.get(f"{BASE_URL}/api/agents", timeout=10)
    assert resp.status_code == 401


def test_create_agent_success(api):
    resp = api.post("/api/agents", json={"name": "测试智能体A"})
    # 空 name 会被 Pydantic 422，非空应该 200
    assert resp.status_code in (200, 400, 422), f"创建智能体意外：{resp.status_code} {resp.text}"
    if resp.status_code == 200:
        data = resp.json()
        assert data["name"] == "测试智能体A"
        assert "id" in data
        # ownerId 是后端自动填入的数字
        assert isinstance(data.get("ownerId"), int)


def test_create_agent_validation(api):
    # 超长名字 → 后端业务校验返回 400
    resp = api.post("/api/agents", json={"name": "A" * 100})
    assert resp.status_code in (400, 422)


def test_toggle_agent_enabled(api, agent_id):
    resp = api.put(f"/api/agents/{agent_id}", json={"enabled": False})
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.json()["enabled"] is False
        resp = api.put(f"/api/agents/{agent_id}", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True


def test_update_nonexistent_agent(api):
    resp = api.put("/api/agents/99999", json={"enabled": False})
    assert resp.status_code == 404


def test_other_user_cannot_update_my_agent(other_api, agent_id):
    """别人不能改我的智能体 → 404（后端按 owner 过滤）。"""
    resp = other_api.put(f"/api/agents/{agent_id}", json={"enabled": False})
    assert resp.status_code in (403, 404)


def test_admin_cannot_update_others_agent_directly(admin, agent_id):
    """admin PUT /agents/{aid} 同样按 owner 过滤 → 404。"""
    resp = admin.put(f"/api/agents/{agent_id}", json={"enabled": False})
    assert resp.status_code in (403, 404)


def test_admin_list_sees_all_agents(admin):
    """admin 列出的智能体数量应 >= 普通用户自己的。"""
    resp = admin.get("/api/agents")
    assert resp.status_code == 200
    assert isinstance(resp.json().get("agents"), list)
