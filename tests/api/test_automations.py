"""
定时任务模块用例（GET / POST / PUT / DELETE）
=============================================
覆盖：列表、新建校验（必须有 agentId）、停用/启用、删除清理、
cron 格式、越权不能改别人的定时任务。
"""
from __future__ import annotations

import pytest
import time


def test_list_automations(api):
    resp = api.get("/api/automations")
    assert resp.status_code == 200
    assert isinstance(resp.json().get("automations", []), list)


def test_create_automation_success(api, agent_id):
    resp = api.post("/api/automations", json={
        "agentId": agent_id,
        "name": "测试定时任务",
        "goal": "每天早上检查一遍行业资讯",
        "cron": "0 9 * * *"
    })
    assert resp.status_code == 200, f"创建失败：{resp.status_code} {resp.text}"
    data = resp.json()
    assert "id" in data
    assert data["enabled"] is True


def test_create_automation_missing_agent():
    """agentId 是必填的，没传 → 422。"""
    from conftest import _register
    api = _register(f"au_{__import__('uuid').uuid4().hex[:6]}", "Auto1234")
    resp = api.post("/api/automations", json={
        "name": "坏任务",
        "goal": "xxx",
        "cron": "* * * * *"
    })
    assert resp.status_code == 422 or resp.status_code == 400


def test_create_automation_invalid_agent(api):
    """agentId 不存在 → 404。"""
    resp = api.post("/api/automations", json={
        "agentId": 99999,
        "name": "不存在的 agent",
        "goal": "xxx",
        "cron": "* * * * *"
    })
    assert resp.status_code == 404


def test_toggle_and_delete_automation(api, agent_id):
    created = api.post("/api/automations", json={
        "agentId": agent_id,
        "name": "开关和删除测试",
        "goal": "临时目标",
        "cron": "* * * * *"
    })
    if created.status_code != 200:
        pytest.skip(f"automation 创建失败 {created.status_code}")
    aid = created.json()["id"]

    # 停用
    resp = api.put(f"/api/automations/{aid}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json().get("ok") is True  # PUT 只回 {"ok": true}

    # 启用
    resp = api.put(f"/api/automations/{aid}", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json().get("ok") is True

    # 删除
    resp = api.delete(f"/api/automations/{aid}")
    assert resp.status_code in (200, 204)


def test_delete_nonexistent_automation(api):
    resp = api.delete("/api/automations/99999")
    assert resp.status_code in (200, 404)


def test_other_user_cannot_modify_my_automation(api, other_api, agent_id):
    aid = api.post("/api/automations", json={
        "agentId": agent_id,
        "name": "我的专属",
        "goal": "专属",
        "cron": "* * * * *"
    }).json()["id"]

    resp = other_api.put(f"/api/automations/{aid}", json={"enabled": False})
    assert resp.status_code in (403, 404)

    api.delete(f"/api/automations/{aid}")


def test_automation_without_token(base_url):
    import requests
    resp = requests.get(f"{base_url}/api/automations", timeout=10)
    assert resp.status_code == 401
