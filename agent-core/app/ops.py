"""
平台管理端接口
==============
管理端：全量用户、用户详情、数据库状态、调度器状态（均需 admin）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from . import db, security

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------ 管理端
@router.get("/admin/users")
def admin_users(user: dict = Depends(security.require_admin)):
    out = []
    for u in db.list_users():
        out.append({**u, "createdAt": str(u.get("created_at") or ""),
                    "tasks": db.scalar("SELECT COUNT(*) FROM tasks WHERE owner_id=:o",
                                       o=u["id"]) or 0})
    return {"users": out}


@router.get("/admin/stats")
def admin_stats(user: dict = Depends(security.require_admin)):
    return {
        "users": db.scalar("SELECT COUNT(*) FROM users") or 0,
        "agents": db.scalar("SELECT COUNT(*) FROM agents") or 0,
        "sessions": db.scalar("SELECT COUNT(*) FROM sessions") or 0,
        "messages": db.scalar("SELECT COUNT(*) FROM messages") or 0,
        "automations": db.scalar("SELECT COUNT(*) FROM automations WHERE enabled=1") or 0,
        "tasks": db.scalar("SELECT COUNT(*) FROM tasks") or 0,
        "artifacts": db.scalar("SELECT COUNT(*) FROM artifacts") or 0,
        "docs": db.scalar("SELECT COUNT(*) FROM knowledge_docs") or 0,
        "db": db.backend(),
    }


@router.delete("/admin/users/{uid}")
def admin_delete_user(uid: int, user: dict = Depends(security.require_admin)):
    """级联删除用户 —— 关联数据一并删除。"""
    if uid == user["id"]:
        raise HTTPException(400, "不能删除自己")
    target = db.get_user_by_id(uid)
    if not target:
        raise HTTPException(404, "用户不存在")
    db.execute("DELETE FROM automations WHERE owner_id=:u", u=uid)
    db.execute("DELETE FROM artifacts WHERE task_id IN (SELECT id FROM tasks WHERE owner_id=:u)", u=uid)
    db.execute("DELETE FROM task_steps WHERE task_id IN (SELECT id FROM tasks WHERE owner_id=:u)", u=uid)
    db.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE owner_id=:u)", u=uid)
    db.execute("DELETE FROM tasks WHERE owner_id=:u", u=uid)
    db.execute("DELETE FROM sessions WHERE owner_id=:u", u=uid)
    db.execute("DELETE FROM agents WHERE owner_id=:u", u=uid)
    db.execute("DELETE FROM users WHERE id=:u", u=uid)
    return {"ok": True}


@router.get("/admin/users/{uid}")
def admin_user_detail(uid: int, user: dict = Depends(security.require_admin)):
    """单个用户的完整画像 —— 统计 + 最近数据。"""
    target = db.get_user_by_id(uid)
    if not target:
        raise HTTPException(404, "用户不存在")
    detail = {
        "id": target["id"],
        "username": target["username"],
        "role": target["role"],
        "createdAt": str(target.get("created_at") or ""),
        "counts": {
            "agents":     db.scalar("SELECT COUNT(*) FROM agents WHERE owner_id=:u", u=uid) or 0,
            "sessions":   db.scalar("SELECT COUNT(*) FROM sessions WHERE owner_id=:u", u=uid) or 0,
            "messages":   db.scalar("SELECT COUNT(*) FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE owner_id=:u)", u=uid) or 0,
            "tasks":      db.scalar("SELECT COUNT(*) FROM tasks WHERE owner_id=:u", u=uid) or 0,
            "automations": db.scalar("SELECT COUNT(*) FROM automations WHERE owner_id=:u", u=uid) or 0,
        },
        "recent_agents": db.query(
            "SELECT id, name, model, skill_ids, enabled FROM agents WHERE owner_id=:u ORDER BY id DESC LIMIT 10", u=uid),
        "recent_sessions": db.query(
            "SELECT id, title, last_message, updated_at FROM sessions WHERE owner_id=:u ORDER BY id DESC LIMIT 10", u=uid),
        "recent_automations": db.query(
            "SELECT id, name, cron_expr, goal, enabled, last_run_at, next_run_at FROM automations WHERE owner_id=:u ORDER BY id DESC LIMIT 10", u=uid),
        "recent_tasks": db.query(
            "SELECT id, goal, status, created_at FROM tasks WHERE owner_id=:u ORDER BY id DESC LIMIT 10", u=uid),
    }
    return detail


@router.get("/admin/db/overview")
def admin_db_overview(user: dict = Depends(security.require_admin)):
    """数据库整体状态 —— 库名、表数、总行数、大小。"""
    backend = db.backend()
    if backend == "mysql":
        rows = db.query(
            "SELECT COUNT(*) AS tables, SUM(table_rows) AS rows_total, "
            "ROUND(SUM(data_length + index_length)/1024/1024, 1) AS mb "
            "FROM information_schema.tables WHERE table_schema = DATABASE()")
        r = rows[0] if rows else {}
        tables = db.query(
            "SELECT table_name, table_rows, "
            "ROUND((data_length + index_length)/1024/1024, 2) AS mb, engine "
            "FROM information_schema.tables WHERE table_schema = DATABASE() "
            "ORDER BY (data_length + index_length) DESC")
        return {"backend": backend, "database": db.scalar("SELECT DATABASE()"),
                "tables": r.get("tables", 0), "rows": int(r.get("rows_total", 0) or 0),
                "size_mb": r.get("mb", 0), "per_table": tables}
    # SQLite 降级
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    per_table = []
    for t in tables:
        n = db.scalar(f"SELECT COUNT(*) FROM `{t['name']}`") or 0
        per_table.append({"table_name": t["name"], "table_rows": n, "mb": None, "engine": "sqlite"})
    return {"backend": backend, "database": "main", "tables": len(tables),
            "rows": sum(r["table_rows"] for r in per_table), "size_mb": None,
            "per_table": per_table}


@router.get("/admin/scheduler/status")
def admin_scheduler_status(user: dict = Depends(security.require_admin)):
    """定时任务调度器状态 —— 当前注册的 jobs。"""
    try:
        from . import scheduler
        jobs = scheduler.list_jobs()
        return {"ok": True, "jobs": jobs, "running": scheduler.is_running()}
    except Exception as e:
        return {"ok": False, "error": str(e), "jobs": [], "running": False}
