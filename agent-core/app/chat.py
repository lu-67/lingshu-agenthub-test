"""
聊天工作台接口（v5 核心）
=======================

POST /api/agents                         创建智能体
GET  /api/agents                         智能体列表
GET  /api/agents/{id}                    详情
PUT  /api/agents/{id}                    修改
DELETE /api/agents/{id}                  删除（内置不可删）

GET  /api/sessions?agentId=xx            会话列表
POST /api/sessions                       新建会话（agentId）
GET  /api/sessions/{id}                  会话详情（含全部消息）
PUT  /api/sessions/{id}                  改标题
DELETE /api/sessions/{id}                删除会话
POST /api/sessions/{id}/send             发送目标 → 执行 → 存过程消息
POST /api/sessions/{id}/approve          授权

POST /api/automations                    创建定时任务
GET  /api/automations                    列表
PUT  /api/automations/{id}               修改
DELETE /api/automations/{id}             删除
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from . import db, engine, llm, security
from .skills import SKILL_IDS, get_skill

router = APIRouter(prefix="/api")


# ---------- Pydantic models ----------
class AgentReq(BaseModel):
    name: str
    avatar: Optional[str] = None
    description: Optional[str] = ""
    systemPrompt: Optional[str] = ""
    model: Optional[str] = "mock"
    skillIds: list[str] = []
    sort: Optional[int] = 80


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    systemPrompt: Optional[str] = None
    model: Optional[str] = None
    skillIds: Optional[list[str]] = None
    enabled: Optional[bool] = None
    sort: Optional[int] = None


class SessionReq(BaseModel):
    agentId: int
    title: Optional[str] = "新对话"


class SendReq(BaseModel):
    content: str
    autoApprove: bool = False  # 测试/简单场景下跳过门禁


class ApproveReq(BaseModel):
    note: str = ""


class AutomationReq(BaseModel):
    agentId: int
    name: str
    cronExpr: str = ""
    cron: str = ""   # 前端兼容字段
    goal: str = ""
    enabled: bool = True

    def cron_value(self) -> str:
        return self.cronExpr or self.cron


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    cronExpr: Optional[str] = None
    goal: Optional[str] = None
    agentId: Optional[int] = None
    enabled: Optional[bool] = None


# ---------- Agents ----------
@router.get("/agents")
def list_agents(user: dict = Depends(security.current_user)):
    return {"agents": db.list_agents(user["id"])}


@router.post("/agents")
def create_agent(req: AgentReq, user: dict = Depends(security.current_user)):
    name = (req.name or "").strip()
    if not name or len(name) > 64:
        raise HTTPException(400, "名称 1-64 字符")
    invalid = [s for s in (req.skillIds or []) if s not in SKILL_IDS]
    if invalid:
        raise HTTPException(400, f"无效技能：{invalid}")
    aid = db.create_agent(user["id"], req.model_dump())
    a = db.get_agent(user["id"], aid)
    return a


@router.put("/agents/{aid}")
def update_agent(aid: int, req: AgentUpdate, user: dict = Depends(security.current_user)):
    if not db.get_agent(user["id"], aid):
        raise HTTPException(404, "智能体不存在")
    if req.skillIds is not None:
        invalid = [s for s in req.skillIds if s not in SKILL_IDS]
        if invalid:
            raise HTTPException(400, f"无效技能：{invalid}")
    db.update_agent(user["id"], aid, req.model_dump(exclude_none=True))
    return db.get_agent(user["id"], aid)


# ---------- Sessions ----------
@router.get("/sessions")
def list_sessions(agentId: Optional[int] = None,
                  limit: int = Query(default=50, ge=1, le=200),
                  user: dict = Depends(security.current_user)):
    return {"sessions": db.list_sessions(user["id"], agentId, limit)}


@router.post("/sessions")
def create_session(req: SessionReq, user: dict = Depends(security.current_user)):
    if not db.get_agent(user["id"], req.agentId):
        raise HTTPException(404, "智能体不存在")
    sid = db.create_session(user["id"], req.agentId, req.title or "新对话")
    sess = db.get_session(user["id"], sid)
    a = db.get_agent(user["id"], req.agentId)
    return {
        "id": sid, "agentId": req.agentId, "agentName": a["name"],
        "agentAvatar": a["avatar"], "title": req.title or "新对话",
        "lastMessage": "", "updatedAt": datetime.now().isoformat(),
        "messages": [],
    }


@router.get("/sessions/{sid}")
def get_session(sid: int, user: dict = Depends(security.current_user)):
    if not db.session_exists(user["id"], sid):
        raise HTTPException(404, "会话不存在")
    sess = db.get_session(user["id"], sid)
    a = db.get_agent(user["id"], sess["agent_id"])
    return {
        "id": sid, "agentId": sess["agent_id"], "agentName": a["name"],
        "agentAvatar": a["avatar"], "title": sess["title"],
        "lastMessage": sess["last_message"],
        "updatedAt": str(sess["updated_at"] or ""),
        "messages": db.list_messages(sid),
    }


# ---------- Core: send + execute ----------
def _agent_pick_skill(agent: dict, goal: str) -> str:
    """Agent 绑定的 skills 列表 → 自动匹配一个，都不匹配时 general。"""
    candidates = agent.get("skillIds") or []
    if not candidates:
        return "general"
    # 先按内置引擎匹配看看命中哪个
    matched = engine.match_skill(goal)["id"]
    if matched in candidates:
        return matched
    # 依次试 agent 允许的 skills
    for sid in candidates:
        if sid in SKILL_IDS:
            return sid
    return "general"


@router.post("/sessions/{sid}/send")
def send_message(sid: int, req: SendReq, user: dict = Depends(security.current_user)):
    if not db.session_exists(user["id"], sid):
        raise HTTPException(404, "会话不存在")
    goal = (req.content or "").strip()
    if len(goal) < 2:
        raise HTTPException(400, "目标至少 2 个字符")
    if len(goal) > 500:
        raise HTTPException(400, "目标不超过 500 个字符")
    if llm.is_injection(goal):
        raise HTTPException(400, "检测到提示词注入或越权指令，已拦截")

    sess = db.get_session(user["id"], sid)
    agent = db.get_agent(user["id"], sess["agent_id"])

    # 1) 存用户消息
    db.add_message(sid, "user", goal, "text", 0)

    # 2) 技能匹配 + 规划（live 模式走 LLM 自由拆步，mock 回退模板）
    skill_id = _agent_pick_skill(agent, goal)
    agent_mode = (agent.get("model") or "mock").lower()
    plan = engine.build_plan(goal, skill_id, mode=agent_mode)

    # 3) 不再发 plan 消息 —— 用户直接看最终回答即可
    #    执行步骤仅存 task.steps 用于内部追踪，不污染对话历史

    # 4) 创建 task 并执行
    tid = db.create_task(user["id"], goal, plan, "mock")
    task = db.get_task(user["id"], tid)
    steps = task["steps"]

    state = db.get_task_state(tid) or {}
    ctx = state.get("context") or {}
    skill = get_skill(task["skillId"]) or get_skill("general")
    ctx = engine.new_context(goal, skill, [s["title"] for s in steps], "mock",
                             approval_gate=any(s["needsApproval"] for s in steps))
    for key, default in (("sources", []), ("fetched", []), ("knowledge", []),
                         ("checklist", []), ("table", {"columns": [], "rows": []})):
        ctx.setdefault(key, default)

    db.update_task(tid, {"status": "running"})
    t0 = time.time()
    done = 0

    for step in steps:
        if step["status"] in ("success", "skipped"):
            done += 1
            continue
        # 敏感门禁
        if step["needsApproval"] and not step["approved"] and not req.autoApprove:
            db.update_step(step["id"], {"status": "waiting"})
            db.update_task(tid, {"status": "waiting_approval"})
            db.save_context(tid, ctx)
            db.add_message(sid, "assistant",
                           f"执行到「{step['title']}」需要人工授权，已暂停。",
                           msg_type="step", step_no=step["seq"],
                           data={"status": "waiting", "taskId": tid,
                                 "stepSeq": step["seq"],
                                 "roleName": step["roleName"],
                                 "title": step["title"]},
                           status="waiting_approval",
                           task_id=tid)
            return {
                "message": "waiting_approval", "sessionId": sid, "taskId": tid,
                "stepSeq": step["seq"],
                "messages": db.list_messages(sid),
            }

        # 执行单步
        db.update_step(step["id"], {"status": "running", "startedAt": datetime.now()})
        step_t0 = time.time()
        try:
            result = engine.run_step(step, ctx, goal)
        except Exception as exc:
            db.update_step(step["id"], {
                "status": "failed", "output": f"步骤执行异常：{exc}",
                "elapsedMs": int((time.time() - step_t0) * 1000),
                "finishedAt": datetime.now()})
            db.update_task(tid, {"status": "failed", "error": str(exc)[:500]})
            db.add_message(sid, "assistant",
                           f"执行失败：{step['title']} → {exc}",
                           msg_type="error", step_no=step["seq"], task_id=tid)
            return {
                "message": "failed", "sessionId": sid, "taskId": tid,
                "error": str(exc), "messages": db.list_messages(sid),
            }

        elapsed_ms = int((time.time() - step_t0) * 1000)
        db.update_step(step["id"], {
            "status": "success", "output": result["summary"],
            "elapsedMs": elapsed_ms, "finishedAt": datetime.now()})
        for art in result["artifacts"]:
            db.add_artifact(tid, art)
        done += 1
        db.update_task(tid, {"stepDone": done,
                             "progress": int(round(done / max(1, len(steps)) * 100))})
        # 注意：不再发 step 消息 —— 内部步骤用户看不到，最终只出一条汇总回答

    # 5) 执行完 → LLM 自然语言汇总，**只发一条 assistant text 消息**
    elapsed = int((time.time() - t0) * 1000)
    fresh = db.get_task(user["id"], tid)
    artifacts = fresh["artifacts"] if fresh else []
    db.update_task(tid, {"status": "completed", "progress": 100, "stepDone": done,
                         "elapsedMs": elapsed})

    # 收集 step 输出给 LLM（但这些不进对话历史）
    step_outputs = []
    for st in fresh["steps"]:
        step_outputs.append({
            "roleName": st["roleName"], "title": st["title"],
            "summary": st.get("output") or "",
        })
    report_text = ctx.get("report")
    sources = ctx.get("sources") or []

    # LLM 自然语言汇总 → 用户直接看到的回答
    final = llm.summarize_run(goal, step_outputs, report_text, sources)
    if not final:
        final = report_text or f"已完成「{goal}」。"

    # 交付物 + 思考过程 都附加在 final 消息的 data 里（不是独立消息）
    final_data = {}
    if artifacts:
        final_data["artifacts"] = [
            {"id": a["id"], "kind": a["kind"], "title": a["title"],
             "format": a["format"], "checksum": a["checksum"]}
            for a in artifacts
        ]
    # 思考过程：plan steps + 执行耗时 —— 前端用 <details> 折叠显示
    final_data["thinking"] = [
        {"role": s["roleName"], "title": s["title"], "elapsedMs": s["elapsedMs"] or 0,
         "status": s["status"]}
        for s in fresh["steps"]
    ]

    db.add_message(sid, "assistant", final,
                   msg_type="text", status="success", task_id=tid,
                   data=final_data)

    return {
        "message": "completed", "sessionId": sid, "taskId": tid,
        "elapsedMs": elapsed, "artifacts": len(artifacts),
        "messages": db.list_messages(sid),
    }


@router.post("/sessions/{sid}/approve")
def approve_session_step(sid: int, req: ApproveReq | None = None,
                         user: dict = Depends(security.current_user)):
    if not db.session_exists(user["id"], sid):
        raise HTTPException(404, "会话不存在")
    # 找本会话最近一个 waiting_approval 的 task
    waiting_task = None
    for t in db.list_tasks(user["id"], 100):
        if t.get("status") == "waiting_approval":
            # 看 messages 里有没有 taskId 引用
            # 简化：直接找 owner=user 且 status=waiting 的 task_id 在 messages
            rows = db.query(
                "SELECT task_id FROM messages WHERE session_id=:s AND task_id IS NOT NULL "
                "ORDER BY id DESC LIMIT 1", s=sid)
            if rows and rows[0]["task_id"] == t["id"]:
                waiting_task = t
                break
    if not waiting_task:
        raise HTTPException(400, "当前没有待授权的步骤")

    tid = waiting_task["id"]
    # 找到 waiting step
    for s in db.list_steps(tid):
        if s["status"] == "waiting":
            db.update_step(s["id"], {"approved": True, "status": "pending"})
            break
    db.update_task(tid, {"status": "running"})

    # 把 send 的后半段再走一次（这里简化：直接调用 send 继续不合适，复制执行逻辑）
    task = db.get_task(user["id"], tid)
    steps = task["steps"]
    state = db.get_task_state(tid) or {}
    ctx = state.get("context") or {}
    skill = get_skill(task["skillId"]) or get_skill("general")
    if not ctx:
        ctx = engine.new_context(task["goal"], skill, [s["title"] for s in steps], "mock")
    for key, default in (("sources", []), ("fetched", []), ("knowledge", []),
                         ("checklist", []), ("table", {"columns": [], "rows": []})):
        ctx.setdefault(key, default)

    db.update_task(tid, {"status": "running"})
    t0 = time.time()
    done = sum(1 for s in steps if s["status"] == "success")

    for step in steps:
        if step["status"] in ("success", "skipped"):
            continue
        if step["needsApproval"] and not step["approved"]:
            db.update_step(step["id"], {"status": "waiting"})
            db.update_task(tid, {"status": "waiting_approval"})
            db.save_context(tid, ctx)
            db.add_message(sid, "assistant",
                           f"执行到「{step['title']}」需要人工授权，已暂停。",
                           msg_type="step", step_no=step["seq"],
                           data={"status": "waiting", "taskId": tid,
                                 "stepSeq": step["seq"]},
                           status="waiting_approval", task_id=tid)
            return {"message": "waiting_approval", "sessionId": sid,
                    "messages": db.list_messages(sid)}

        db.update_step(step["id"], {"status": "running", "startedAt": datetime.now()})
        step_t0 = time.time()
        try:
            result = engine.run_step(step, ctx, task["goal"])
        except Exception as exc:
            db.update_step(step["id"], {"status": "failed", "output": f"{exc}",
                                        "elapsedMs": int((time.time() - step_t0) * 1000),
                                        "finishedAt": datetime.now()})
            db.update_task(tid, {"status": "failed", "error": str(exc)[:500]})
            db.add_message(sid, "assistant", f"执行失败：{exc}",
                           msg_type="error", step_no=step["seq"], task_id=tid)
            return {"message": "failed", "messages": db.list_messages(sid)}

        elapsed_ms = int((time.time() - step_t0) * 1000)
        db.update_step(step["id"], {"status": "success", "output": result["summary"],
                                     "elapsedMs": elapsed_ms,
                                     "finishedAt": datetime.now()})
        for art in result["artifacts"]:
            db.add_artifact(tid, art)
        done += 1
        db.update_task(tid, {"stepDone": done,
                             "progress": int(round(done / max(1, len(steps)) * 100))})
        # 注意：approve 路径也不再发 step 消息

    elapsed = int((time.time() - t0) * 1000)
    fresh = db.get_task(user["id"], tid)
    artifacts = fresh["artifacts"] if fresh else []
    db.update_task(tid, {"status": "completed", "progress": 100,
                         "stepDone": done, "elapsedMs": elapsed})

    step_outputs = [{"roleName": st["roleName"], "title": st["title"],
                     "summary": st.get("output") or ""}
                    for st in fresh["steps"]]
    report_text = ctx.get("report")
    sources = ctx.get("sources") or []
    final = llm.summarize_run(task["goal"], step_outputs, report_text, sources)
    if not final:
        final = report_text or f"已完成「{task['goal']}」。"

    final_data = {}
    if artifacts:
        final_data["artifacts"] = [
            {"id": a["id"], "kind": a["kind"], "title": a["title"],
             "format": a["format"], "checksum": a["checksum"]}
            for a in artifacts
        ]
    final_data["thinking"] = [
        {"role": s["roleName"], "title": s["title"], "elapsedMs": s["elapsedMs"] or 0,
         "status": s["status"]}
        for s in fresh["steps"]
    ]
    db.add_message(sid, "assistant", final,
                   msg_type="text", status="success", task_id=tid,
                   data=final_data)

    return {"message": "completed", "sessionId": sid, "elapsedMs": elapsed,
            "messages": db.list_messages(sid)}


# ---------- Automations ----------
@router.get("/artifacts/{aid}/download")
def download_artifact(aid: int, user: dict = Depends(security.current_user)):
    art = db.get_artifact(user["id"], aid)
    if not art:
        raise HTTPException(404, "交付物不存在")
    media = "text/csv; charset=utf-8" if art["format"] == "csv" else \
            "text/markdown; charset=utf-8"
    filename = quote(art["title"] or f"artifact-{aid}.{art['format']}")
    return Response(content=art["content"], media_type=media,
                    headers={"Content-Disposition":
                             f"attachment; filename*=UTF-8''{filename}"})


@router.get("/automations")
def list_automations(user: dict = Depends(security.current_user)):
    return {"automations": db.list_automations(user["id"])}


@router.post("/automations")
def create_automation(req: AutomationReq, user: dict = Depends(security.current_user)):
    if not db.get_agent(user["id"], req.agentId):
        raise HTTPException(404, "智能体不存在")
    cron = req.cron_value()
    aid = db.create_automation(user["id"], req.agentId, req.name,
                               cron, req.goal)
    # 同步到调度器
    try:
        from . import scheduler
        if req.enabled:
            scheduler.add_job(aid, cron)
    except Exception:
        pass
    return {"id": aid, "agentId": req.agentId, "name": req.name,
            "cronExpr": cron, "goal": req.goal, "enabled": req.enabled}


@router.put("/automations/{aid}")
def update_automation(aid: int, req: AutomationUpdate,
                      user: dict = Depends(security.current_user)):
    prev = db.get_automation(aid)
    if not prev or prev["owner_id"] != user["id"]:
        raise HTTPException(404, "定时任务不存在")
    db.update_automation(user["id"], aid, req.model_dump(exclude_none=True))
    # 同步调度器
    try:
        from . import scheduler
        new_cron = req.cronExpr if req.cronExpr is not None else prev.get("cron_expr")
        new_enabled = req.enabled if req.enabled is not None else prev.get("enabled")
        scheduler.update_job(aid, cron_expr=new_cron, enabled=new_enabled)
    except Exception:
        pass
    return {"ok": True}


@router.delete("/automations/{aid}")
def delete_automation(aid: int, user: dict = Depends(security.current_user)):
    if not db.delete_automation(user["id"], aid):
        raise HTTPException(404, "定时任务不存在")
    # 同步调度器
    try:
        from . import scheduler
        scheduler.remove_job(aid)
    except Exception:
        pass
    return {"ok": True, "id": aid}
