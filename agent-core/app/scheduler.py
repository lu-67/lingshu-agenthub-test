"""APScheduler 定时任务调度器。

工作方式：
- 启动时从 DB 加载所有 enabled 的 automations，注册 cron job
- 每次触发完全复用 chat.send_message 的执行链路：
  1. 创建 session + 存 user 消息
  2. engine.build_plan → db.create_task → engine.run_step 循环 → llm.summarize_run
  3. 存 assistant text 消息（thinking + artifacts）
  4. 更新 last_run_at / next_run_at

chat.py 的 automations CRUD 会调用 add_job / remove_job / update_job 同步。
"""
from __future__ import annotations

import datetime as _dt
import logging
import threading
import time as _time
from typing import Optional

log = logging.getLogger("scheduler")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APS_OK = True
except ImportError:
    _APS_OK = False
    BackgroundScheduler = None  # type: ignore


# ---------- 单例 ----------
_scheduler: Optional[BackgroundScheduler] = None
_lock = threading.Lock()

_JOB_PREFIX = "auto_"


def _job_id(auto_id: int) -> str:
    return f"{_JOB_PREFIX}{auto_id}"


def _parse_cron(expr: str):
    """把 '0 9 * * *' 拆成 CronTrigger。"""
    parts = (expr or "").strip().split()
    if len(parts) == 6:
        parts = parts[:5]
    if len(parts) != 5:
        return None
    second, minute, hour, day, month = parts
    try:
        return CronTrigger(
            second=second if second != "*" else None,
            minute=minute if minute != "*" else None,
            hour=hour if hour != "*" else None,
            day=day if day != "*" else None,
            month=month if month != "*" else None,
            day_of_week=None,
        )
    except Exception as e:
        log.warning("cron parse fail %r: %s", expr, e)
        return None


def init() -> bool:
    """启动调度器 + 从 DB 加载所有启用的定时任务。"""
    global _scheduler
    if not _APS_OK:
        log.error("APScheduler 未安装。pip install APScheduler")
        return False
    with _lock:
        if _scheduler is not None:
            return True
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        _scheduler.start()
        log.info("[scheduler] APScheduler started (Asia/Shanghai)")
    _reload_all()
    return True


def shutdown():
    global _scheduler
    with _lock:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            log.info("[scheduler] stopped")


def is_running() -> bool:
    """调度器是否已启动。"""
    return _scheduler is not None


def list_jobs() -> list[dict]:
    """当前已注册的定时任务（APScheduler jobs）。"""
    if _scheduler is None:
        return []
    out = []
    for j in _scheduler.get_jobs():
        out.append({
            "job_id": j.id,
            "next_run": str(j.next_run_time) if j.next_run_time else None,
            "trigger": str(j.trigger),
            "enabled": bool(j.next_run_time is not None),
        })
    return out


def _reload_all():
    """从 DB 全量加载 enabled 的 automations。"""
    from . import db
    if _scheduler is None:
        return
    for job in list(_scheduler.get_jobs()):
        if job.id.startswith(_JOB_PREFIX):
            _scheduler.remove_job(job.id)
    try:
        rows = db.list_automations_all_enabled()
    except Exception as e:
        log.warning("load automations fail: %s", e)
        return
    for r in rows:
        _add_job_internal(r["id"], r["cron_expr"])
    log.info("[scheduler] loaded %d automations", len(rows))


def _add_job_internal(auto_id: int, cron_expr: str):
    if _scheduler is None:
        return
    trigger = _parse_cron(cron_expr)
    if trigger is None:
        log.warning("skip auto %d: bad cron %r", auto_id, cron_expr)
        return
    jid = _job_id(auto_id)
    if _scheduler.get_job(jid):
        _scheduler.remove_job(jid)
    _scheduler.add_job(
        _run_automation,
        trigger=trigger,
        id=jid,
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1,
        args=[auto_id],
    )
    job = _scheduler.get_job(jid)
    if job and job.next_run_time:
        from . import db
        try:
            db.update_automation_next(auto_id, job.next_run_time)
        except Exception:
            pass
    log.info("[scheduler] + auto %d cron=%s next=%s", auto_id, cron_expr,
             job.next_run_time if job else None)


def add_job(auto_id: int, cron_expr: str):
    if _scheduler is None:
        return False
    _add_job_internal(auto_id, cron_expr)
    return True


def remove_job(auto_id: int):
    if _scheduler is None:
        return
    jid = _job_id(auto_id)
    if _scheduler.get_job(jid):
        _scheduler.remove_job(jid)
        log.info("[scheduler] - auto %d", auto_id)


def update_job(auto_id: int, cron_expr: Optional[str] = None, enabled: Optional[bool] = None):
    if enabled is False:
        remove_job(auto_id)
        return
    if cron_expr:
        remove_job(auto_id)
        add_job(auto_id, cron_expr)
    else:
        from . import db
        try:
            rows = db.list_automations_all_enabled()
            for r in rows:
                if r["id"] == auto_id:
                    add_job(auto_id, r["cron_expr"])
                    break
        except Exception:
            pass


# ---------- 复用 chat.send_message 执行链路 ----------
def _pick_skill(agent: dict, goal: str) -> str:
    """和 chat._agent_pick_skill 一样的逻辑。"""
    from . import db, engine
    candidates = agent.get("skillIds") or []
    if not candidates:
        return "general"
    matched = engine.match_skill(goal)["id"]
    if matched in candidates:
        return matched
    for sid in candidates:
        return sid
    return "general"


def _run_automation(auto_id: int):
    """执行定时任务 —— 完全复用 chat.send_message 的执行链路。"""
    log.info("[scheduler] >>> fire auto %d at %s", auto_id, _dt.datetime.now())
    from . import db, llm, engine

    # 1. 查 automation + user + agent
    auto = db.get_automation(auto_id)
    if not auto:
        log.warning("auto %d not found, skip", auto_id)
        remove_job(auto_id)
        return
    user = db.get_user_by_id(auto["owner_id"])
    agent = db.get_agent(auto["owner_id"], auto["agent_id"])
    if not user or not agent:
        log.warning("auto %d: user/agent missing, skip", auto_id)
        return

    goal = str(auto["goal"]).strip()
    if len(goal) < 2:
        log.warning("auto %d: goal too short, skip", auto_id)
        return

    # 2. 更新 last_run_at
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        db.update_automation_last(auto_id, now)
    except Exception:
        pass

    # 3. 创建 session + 存 user 消息
    sid = db.create_session(user["id"], agent["id"], auto["name"])
    db.add_message(sid, "user", goal, "text", 0)

    try:
        # 4. build_plan
        skill_id = _pick_skill(agent, goal)
        agent_mode = (agent.get("model") or "mock").lower()
        plan = engine.build_plan(goal, skill_id, mode=agent_mode)
        if not plan.get("steps"):
            plan = engine.build_plan(goal, "general", mode="mock")

        # 5. create_task（plan 会被展开成 steps 存进 task_steps 表）
        tid = db.create_task(user["id"], goal, plan, agent_mode)
        task = db.get_task(user["id"], tid)
        steps = task["steps"]

        # 6. 准备执行上下文
        state = db.get_task_state(tid) or {}
        ctx = state.get("context") or {}
        from .skills import get_skill as _get_skill
        skill = _get_skill(task["skillId"]) or _get_skill("general")
        ctx = engine.new_context(goal, skill, [s["title"] for s in steps], "mock",
                                 approval_gate=False)
        for key, default in (("sources", []), ("fetched", []), ("knowledge", []),
                             ("checklist", []), ("table", {"columns": [], "rows": []})):
            ctx.setdefault(key, default)

        db.update_task(tid, {"status": "running"})
        t0 = _time.time()
        done = 0

        # 7. 逐 step 执行（定时任务自动审批，不走授权门禁）
        for step in steps:
            if step["status"] in ("success", "skipped"):
                done += 1
                continue
            db.update_step(step["id"], {"status": "running", "startedAt": _dt.datetime.now()})
            step_t0 = _time.time()
            try:
                result = engine.run_step(step, ctx, goal)
            except Exception as exc:
                db.update_step(step["id"], {
                    "status": "failed", "output": f"定时任务异常：{exc}",
                    "elapsedMs": int((_time.time() - step_t0) * 1000),
                    "finishedAt": _dt.datetime.now()})
                db.update_task(tid, {"status": "failed", "error": str(exc)[:500]})
                log.exception("[scheduler] auto %d step fail: %s", auto_id, exc)
                break

            elapsed_ms = int((_time.time() - step_t0) * 1000)
            db.update_step(step["id"], {
                "status": "success", "output": result["summary"],
                "elapsedMs": elapsed_ms, "finishedAt": _dt.datetime.now()})
            for art in result["artifacts"]:
                db.add_artifact(tid, art)
            done += 1
            db.update_task(tid, {"stepDone": done,
                                 "progress": int(round(done / max(1, len(steps)) * 100))})

        # 8. 完成 → LLM 汇总
        fresh = db.get_task(user["id"], tid)
        elapsed = int((_time.time() - t0) * 1000)
        db.update_task(tid, {"status": "completed", "progress": 100, "stepDone": done,
                             "elapsedMs": elapsed})
        artifacts = fresh["artifacts"] if fresh else []

        step_outputs = []
        for st in fresh["steps"]:
            step_outputs.append({
                "roleName": st["roleName"], "title": st["title"],
                "summary": st.get("output") or "",
            })
        report_text = ctx.get("report")
        sources = ctx.get("sources") or []

        final = llm.summarize_run(goal, step_outputs, report_text, sources)
        if not final:
            final = report_text or f"定时任务「{auto['name']}」已完成。"

        # 9. 存 assistant 消息
        final_data = {
            "thinking": [
                {"role": s["roleName"], "title": s["title"],
                 "elapsedMs": s["elapsedMs"] or 0, "status": s["status"]}
                for s in fresh["steps"]
            ]
        }
        if artifacts:
            final_data["artifacts"] = [
                {"id": a["id"], "kind": a["kind"], "title": a["title"],
                 "format": a["format"], "checksum": a["checksum"]}
                for a in artifacts
            ]
        db.add_message(sid, "assistant", final, "text", data=final_data)
        log.info("[scheduler] ✓ auto %d → session %d task %d steps=%d",
                 auto_id, sid, tid, len(steps))

    except Exception as e:
        log.exception("[scheduler] ✗ auto %d fail: %s", auto_id, e)
        # 存一条错误消息让用户看到
        try:
            db.add_message(sid, "assistant",
                           f"⚠️ 定时任务「{auto['name']}」执行失败：{e}",
                           "text", data={"error": True})
        except Exception:
            pass

    # 10. 更新 next_run_at
    job = _scheduler.get_job(_job_id(auto_id)) if _scheduler else None
    if job and job.next_run_time:
        try:
            db.update_automation_next(auto_id, job.next_run_time)
        except Exception:
            pass
