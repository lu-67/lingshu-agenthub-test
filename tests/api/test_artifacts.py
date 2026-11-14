"""
交付物下载用例
==============
覆盖：正常下载、不存在的交付物 404、无 token 401、伪造 token 401、
下载内容是 send 执行产出的真实文件。
"""
from __future__ import annotations

import pytest


def _get_real_artifact_id(api, agent_id) -> int:
    """跑一次 send，从返回的 assistant 消息里拿到第一个 artifact id。"""
    sid = api.post("/api/sessions", json={"agentId": agent_id}).json()["id"]
    result = api.post(f"/api/sessions/{sid}/send",
                      json={"content": "输出一份测试报告"})
    assert result.status_code == 200
    msgs = result.json().get("messages", [])
    for m in msgs:
        if m["role"] == "assistant":
            arts = m.get("data", {}).get("artifacts", [])
            if arts:
                return arts[0]["id"]
    pytest.skip("本次 send 没产出交付物")


def test_download_artifact_success(api, agent_id):
    aid = _get_real_artifact_id(api, agent_id)
    resp = api.get(f"/api/artifacts/{aid}/download")
    assert resp.status_code == 200
    # 返回内容应该不为空
    assert len(resp.content) > 0


def test_download_nonexistent_artifact(api):
    resp = api.get("/api/artifacts/99999/download")
    assert resp.status_code == 404


def test_download_without_token(base_url):
    import requests
    resp = requests.get(f"{base_url}/api/artifacts/1/download", timeout=10)
    assert resp.status_code == 401


def test_download_with_fake_token(base_url):
    import requests
    resp = requests.get(f"{base_url}/api/artifacts/1/download",
                        headers={"Authorization": "Bearer a.b.c"}, timeout=10)
    assert resp.status_code == 401


def test_download_content_type(api, agent_id):
    aid = _get_real_artifact_id(api, agent_id)
    resp = api.get(f"/api/artifacts/{aid}/download")
    assert resp.status_code == 200
    # 下载接口应该返回文本类 content-type
    ct = resp.headers.get("Content-Type", "")
    assert "text" in ct or "csv" in ct or "markdown" in ct
