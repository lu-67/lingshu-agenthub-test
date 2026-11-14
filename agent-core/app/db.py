"""
数据访问层（SQLAlchemy Core + 原生 SQL）
======================================
v5.0 数据模型（会话式智能体工作台）：

  users             账号
  tasks             遗留任务型表（会话执行时写入）
  task_steps        任务步骤
  artifacts         交付物（Markdown / CSV / 审核清单）
  knowledge_docs    RAG 知识库文档
  agents            智能体（6 内置 + 用户自建）
  sessions          会话（一次智能体对话）
  messages          消息（会话内逐条，含思考过程步骤）
  automations       定时任务（APScheduler 注册）

默认 MySQL 3307 / 库 nexus_agent；连不上自动降级 SQLite，保证零配置可跑。
启动时清理 v3/v4 遗留表（conversations / workflows / channels / roles /
skill_settings / runs / eval_runs ...），让库结构与代码完全一致。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, MetaData,
                        String, Table, Text, create_engine, func, text)

from . import config

metadata = MetaData()

users = Table("users", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("username", String(64), unique=True, nullable=False),
              Column("password_hash", String(255), nullable=False),
              Column("role", String(16), nullable=False, default="USER"),
              Column("created_at", DateTime, nullable=False, server_default=func.now()))

tasks = Table("tasks", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("owner_id", Integer, nullable=False, index=True),
              Column("goal", Text, nullable=False),
              Column("skill_id", String(32), nullable=False, default="general"),
              Column("skill_name", String(64), nullable=False, default="通用任务"),
              Column("status", String(20), nullable=False, default="planned", index=True),
              Column("mode", String(16), nullable=False, default="mock"),
              Column("summary", Text, nullable=False, default=""),
              Column("progress", Integer, nullable=False, default=0),
              Column("step_total", Integer, nullable=False, default=0),
              Column("step_done", Integer, nullable=False, default=0),
              Column("elapsed_ms", Integer, nullable=False, default=0),
              Column("error", Text, nullable=False, default=""),
              Column("context", Text, nullable=False, default="{}"),
              Column("day", String(10), nullable=False, default="", index=True),
              Column("created_at", DateTime, nullable=False, server_default=func.now()),
              Column("updated_at", DateTime, nullable=False, server_default=func.now()),
              Column("finished_at", DateTime))

task_steps = Table("task_steps", metadata,
                   Column("id", Integer, primary_key=True, autoincrement=True),
                   Column("task_id", Integer, nullable=False, index=True),
                   Column("seq", Integer, nullable=False, default=1),
                   Column("role_key", String(32), nullable=False, default=""),
                   Column("role_name", String(64), nullable=False, default=""),
                   Column("role_avatar", String(16), nullable=False, default="🤖"),
                   Column("action", String(32), nullable=False, default=""),
                   Column("title", String(255), nullable=False, default=""),
                   Column("input", Text, nullable=False, default=""),
                   Column("output", Text, nullable=False, default=""),
                   Column("status", String(20), nullable=False, default="pending"),
                   Column("needs_approval", Boolean, nullable=False, default=False,
                          server_default=text("0")),
                   Column("approved", Boolean, nullable=False, default=False,
                          server_default=text("0")),
                   Column("elapsed_ms", Integer, nullable=False, default=0),
                   Column("started_at", DateTime),
                   Column("finished_at", DateTime))

artifacts = Table("artifacts", metadata,
                  Column("id", Integer, primary_key=True, autoincrement=True),
                  Column("task_id", Integer, nullable=False, index=True),
                  Column("kind", String(16), nullable=False, default="report"),
                  Column("title", String(255), nullable=False, default=""),
                  Column("format", String(16), nullable=False, default="md"),
                  Column("content", Text, nullable=False, default=""),
                  Column("size", Integer, nullable=False, default=0),
                  Column("step_seq", Integer, nullable=False, default=0),
                  Column("checksum", String(32), nullable=False, default=""),
                  Column("created_at", DateTime, nullable=False, server_default=func.now()))

knowledge_docs = Table("knowledge_docs", metadata,
                       Column("id", Integer, primary_key=True, autoincrement=True),
                       Column("owner_id", Integer, nullable=False),
                       Column("title", String(255), nullable=False),
                       Column("doc_key", String(32), nullable=False, default=""),
                       Column("content", Text, nullable=False, default=""),
                       Column("chunks", Integer, nullable=False, default=0),
                       Column("source", String(32), nullable=False, default="manual"),
                       Column("created_at", DateTime, nullable=False, server_default=func.now()))

# ---------------- v5 核心：智能体/会话/消息/定时任务 ----------------
agents = Table("agents", metadata,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("owner_id", Integer, nullable=False, index=True),
              Column("name", String(64), nullable=False),
              Column("avatar", String(16), nullable=False, default="🤖"),
              Column("description", String(255), nullable=False, default=""),
              Column("system_prompt", Text, nullable=False, default=""),
              Column("model", String(32), nullable=False, default="mock"),
              Column("skill_ids", Text, nullable=False, default="[]"),   # JSON array
              Column("enabled", Boolean, nullable=False, default=True, server_default=text("1")),
              Column("is_builtin", Boolean, nullable=False, default=False, server_default=text("0")),
              Column("sort", Integer, nullable=False, default=50),
              Column("created_at", DateTime, nullable=False, server_default=func.now()))

sessions = Table("sessions", metadata,
                 Column("id", Integer, primary_key=True, autoincrement=True),
                 Column("owner_id", Integer, nullable=False, index=True),
                 Column("agent_id", Integer, nullable=False, index=True),
                 Column("title", String(120), nullable=False, default="新对话"),
                 Column("last_message", Text, nullable=False, default=""),
                 Column("updated_at", DateTime, nullable=False, server_default=func.now()))

messages = Table("messages", metadata,
                 Column("id", Integer, primary_key=True, autoincrement=True),
                 Column("session_id", Integer, nullable=False, index=True),
                 Column("role", String(16), nullable=False, default="user"),
                 Column("content", Text, nullable=False, default=""),
                 Column("msg_type", String(20), nullable=False, default="text"),  # text/step/artifacts/plan/error
                 Column("step_no", Integer, nullable=False, default=0),
                 Column("data", Text, nullable=False, default="{}"),              # JSON（计划/步骤详情/交付物列表）
                 Column("status", String(16), nullable=False, default="success"),
                 Column("task_id", Integer, nullable=True),
                 Column("created_at", DateTime, nullable=False, server_default=func.now()))

automations = Table("automations", metadata,
                    Column("id", Integer, primary_key=True, autoincrement=True),
                    Column("owner_id", Integer, nullable=False, index=True),
                    Column("agent_id", Integer, nullable=False),
                    Column("name", String(64), nullable=False),
                    Column("cron_expr", String(40), nullable=False),
                    Column("goal", Text, nullable=False),
                    Column("enabled", Boolean, nullable=False, default=True, server_default=text("1")),
                    Column("last_run_at", DateTime),
                    Column("next_run_at", DateTime),
                    Column("created_at", DateTime, nullable=False, server_default=func.now()))

_engine = None
_backend = "mysql"

LEGACY_TABLES = ("conversations", "feedback", "workflows",
                 "prompt_versions", "channels", "api_keys",
                 "roles", "skill_settings", "runs", "eval_runs")


def _mysql_url(include_db: bool = True) -> str:
    db = "/" + config.MYSQL_DB if include_db else "/"
    return (f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
            f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}{db}?charset=utf8mb4")


def _ensure_mysql_database() -> None:
    eng = create_engine(_mysql_url(False), pool_pre_ping=True, future=True)
    with eng.begin() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS {config.MYSQL_DB} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    eng.dispose()


def get_engine():
    global _engine, _backend
    if _engine is not None:
        return _engine
    try:
        _ensure_mysql_database()
        eng = create_engine(_mysql_url(True), pool_pre_ping=True, future=True,
                            pool_recycle=3600)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        _engine, _backend = eng, "mysql"
        print("[db] backend = MySQL "
              f"{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}", flush=True)
    except Exception as exc:
        if not config.DB_FALLBACK_SQLITE:
            raise
        config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{config.SQLITE_PATH}", future=True)
        _backend = "sqlite"
        print(f"[db] MySQL 不可用({type(exc).__name__})，降级 SQLite: "
              f"{config.SQLITE_PATH}", flush=True)
    return _engine


def backend() -> str:
    if _engine is None:
        get_engine()
    return _backend


def query(sql: str, **params) -> list[dict]:
    with get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(text(sql), params).mappings().all()]


def execute(sql: str, **params) -> int:
    """执行写操作，返回新插入行主键（无自增则返回影响行数）。"""
    with get_engine().begin() as conn:
        result = conn.execute(text(sql), params)
        return int(result.lastrowid or result.rowcount)


def scalar(sql: str, **params):
    with get_engine().connect() as conn:
        row = conn.execute(text(sql), params).first()
        return row[0] if row else None


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _loads(raw, default):
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


# ------------------------------------------------------------------ 初始化
def init_db(password_hasher) -> None:
    eng = get_engine()
    # 清理 v3 遗留表（新版本不再使用），让库结构与教程/文档一致
    with eng.begin() as conn:
        for t in LEGACY_TABLES:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {t}"))
            except Exception:
                pass
    metadata.create_all(eng)

    for username, pwd, role in (("admin", "admin123", "ADMIN"),
                                ("tester", "tester123", "USER")):
        if not query("SELECT id FROM users WHERE username=:u", u=username):
            execute("INSERT INTO users(username,password_hash,role) VALUES(:u,:p,:r)",
                    u=username, p=password_hasher(pwd), r=role)
    for row in query("SELECT id FROM users"):
        seed_user_defaults(row["id"])
    print("[db] 初始化完成，种子账号 admin/admin123、tester/tester123", flush=True)


def seed_user_defaults(user_id: int) -> None:
    """新用户首次登录即拥有 6 个内置智能体。"""
    seed_builtin_agents(user_id)


# ------------------------------------------------------------------ 用户
def get_user_by_name(username: str) -> dict | None:
    rows = query("SELECT * FROM users WHERE username=:u", u=username)
    return rows[0] if rows else None


def get_user_by_id(uid: int) -> dict | None:
    rows = query("SELECT * FROM users WHERE id=:i", i=uid)
    return rows[0] if rows else None


def create_user(username: str, password_hash: str, role: str = "USER") -> int:
    uid = execute("INSERT INTO users(username,password_hash,role) VALUES(:u,:p,:r)",
                  u=username, p=password_hash, r=role)
    seed_user_defaults(uid)
    return uid


def list_users() -> list[dict]:
    return query("SELECT id,username,role,created_at FROM users ORDER BY id")


# ------------------------------------------------------------------ 任务
def _step_to_dict(r: dict, with_output: bool = True) -> dict:
    out = {
        "id": r["id"], "taskId": r["task_id"], "seq": r["seq"],
        "roleKey": r["role_key"], "roleName": r["role_name"],
        "roleAvatar": r["role_avatar"], "action": r["action"],
        "title": r["title"], "status": r["status"],
        "needsApproval": bool(r["needs_approval"]), "approved": bool(r["approved"]),
        "elapsedMs": r["elapsed_ms"],
        "startedAt": str(r["started_at"] or ""), "finishedAt": str(r["finished_at"] or ""),
    }
    if with_output:
        out["input"] = r["input"] or ""
        out["output"] = r["output"] or ""
    return out


def _artifact_to_dict(r: dict, with_content: bool = False) -> dict:
    out = {"id": r["id"], "taskId": r["task_id"], "kind": r["kind"],
           "title": r["title"], "format": r["format"], "size": r["size"],
           "stepSeq": r["step_seq"], "checksum": r["checksum"] or "",
           "createdAt": str(r["created_at"] or "")}
    if with_content:
        out["content"] = r["content"] or ""
    return out


def _task_to_dict(r: dict) -> dict:
    return {
        "id": r["id"], "goal": r["goal"], "skillId": r["skill_id"],
        "skillName": r["skill_name"], "status": r["status"], "mode": r["mode"],
        "summary": r["summary"] or "", "progress": r["progress"],
        "stepTotal": r["step_total"], "stepDone": r["step_done"],
        "elapsedMs": r["elapsed_ms"], "error": r["error"] or "",
        "createdAt": str(r["created_at"] or ""),
        "updatedAt": str(r["updated_at"] or ""),
        "finishedAt": str(r["finished_at"] or ""),
    }


def create_task(owner_id: int, goal: str, plan: dict, mode: str = "mock") -> int:
    tid = execute(
        "INSERT INTO tasks(owner_id,goal,skill_id,skill_name,status,mode,summary,progress,"
        "step_total,step_done,elapsed_ms,error,context,day,created_at,updated_at) "
        "VALUES(:o,:g,:si,:sn,:st,:m,:su,0,:tot,0,0,'','{}',:dy,:c,:u)",
        o=owner_id, g=goal, si=plan["skillId"], sn=plan["skillName"], st="planned",
        m=mode, su=plan.get("summary", ""), tot=len(plan["steps"]), dy=today(),
        c=datetime.now(), u=datetime.now())
    for s in plan["steps"]:
        execute(
            "INSERT INTO task_steps(task_id,seq,role_key,role_name,role_avatar,action,title,"
            "input,output,status,needs_approval,approved,elapsed_ms) "
            "VALUES(:t,:q,:rk,:rn,:ra,:a,:ti,:in,'','pending',:na,0,0)",
            t=tid, q=s["seq"], rk=s["roleKey"], rn=s["roleName"],
            ra=s.get("roleAvatar", "🤖"), a=s["action"], ti=s["title"],
            **{"in": s["input"]}, na=1 if s.get("needsApproval") else 0)
    return tid


def list_tasks(owner_id: int, limit: int = 50, status: str | None = None,
               keyword: str | None = None) -> list[dict]:
    sql = ("SELECT t.*, (SELECT COUNT(*) FROM artifacts a WHERE a.task_id=t.id) "
           "AS artifact_count FROM tasks t WHERE t.owner_id=:o")
    params: dict = {"o": owner_id, "n": int(limit)}
    if status:
        sql += " AND t.status=:st"
        params["st"] = status
    if keyword:
        sql += " AND t.goal LIKE :kw"
        params["kw"] = f"%{keyword}%"
    sql += " ORDER BY t.id DESC LIMIT :n"
    out = []
    for r in query(sql, **params):
        d = _task_to_dict(r)
        d["artifactCount"] = int(r.get("artifact_count") or 0)
        out.append(d)
    return out


def get_task(owner_id: int, tid: int) -> dict | None:
    rows = query("SELECT * FROM tasks WHERE id=:i AND owner_id=:o", i=tid, o=owner_id)
    if not rows:
        return None
    task = _task_to_dict(rows[0])
    task["steps"] = [_step_to_dict(s) for s in
                     query("SELECT * FROM task_steps WHERE task_id=:t ORDER BY seq", t=tid)]
    task["artifacts"] = [_artifact_to_dict(a) for a in
                         query("SELECT * FROM artifacts WHERE task_id=:t ORDER BY id", t=tid)]
    return task


def get_task_raw(tid: int) -> dict | None:
    rows = query("SELECT * FROM tasks WHERE id=:i", i=tid)
    return _task_to_dict(rows[0]) if rows else None


def get_task_state(tid: int) -> dict | None:
    """执行引擎需要的内部状态：状态 + 已存上下文（授权后继续执行靠它）。"""
    rows = query("SELECT id,owner_id,status,step_total,step_done,context,mode,skill_id,"
                 "skill_name FROM tasks WHERE id=:i", i=tid)
    if not rows:
        return None
    r = rows[0]
    return {"id": r["id"], "ownerId": r["owner_id"], "status": r["status"],
            "stepTotal": r["step_total"], "stepDone": r["step_done"],
            "context": _loads(r["context"], {}), "mode": r["mode"],
            "skillId": r["skill_id"], "skillName": r["skill_name"]}


def save_context(tid: int, ctx: dict) -> None:
    execute("UPDATE tasks SET context=:c,updated_at=:u WHERE id=:i",
            c=json.dumps(ctx, ensure_ascii=False, default=str), u=datetime.now(), i=tid)


def update_task(tid: int, d: dict) -> None:
    old = get_task_raw(tid)
    if not old:
        return
    m = {**old, **{k: v for k, v in d.items() if v is not None}}
    execute("UPDATE tasks SET status=:st,mode=:m,summary=:su,progress=:pr,step_done=:sd,"
            "elapsed_ms=:el,error=:er,updated_at=:u,finished_at=:f WHERE id=:i",
            st=m["status"], m=m.get("mode", "mock"), su=m.get("summary", ""),
            pr=int(m.get("progress", 0)), sd=int(m.get("stepDone", 0)),
            el=int(m.get("elapsedMs", 0)), er=(m.get("error") or "")[:1000],
            u=datetime.now(),
            f=datetime.now() if m["status"] in ("completed", "failed", "cancelled") else None,
            i=tid)


def list_steps(tid: int) -> list[dict]:
    return [_step_to_dict(s) for s in
            query("SELECT * FROM task_steps WHERE task_id=:t ORDER BY seq", t=tid)]


def update_step(sid: int, d: dict) -> None:
    fields, params = [], {"i": sid}
    mapping = {"status": "status", "output": "output", "elapsedMs": "elapsed_ms",
               "approved": "approved", "finishedAt": "finished_at",
               "startedAt": "started_at"}
    for k, col in mapping.items():
        if k in d and d[k] is not None:
            fields.append(f"{col}=:{k}")
            params[k] = (1 if d[k] else 0) if k == "approved" else d[k]
    if not fields:
        return
    execute(f"UPDATE task_steps SET {', '.join(fields)} WHERE id=:i", **params)


def reset_task(tid: int) -> None:
    execute("UPDATE task_steps SET status='pending',output='',elapsed_ms=0,approved=0,"
            "started_at=NULL,finished_at=NULL WHERE task_id=:t", t=tid)
    execute("DELETE FROM artifacts WHERE task_id=:t", t=tid)
    execute("UPDATE tasks SET status='planned',progress=0,step_done=0,elapsed_ms=0,"
            "error='',finished_at=NULL,updated_at=:u WHERE id=:i", u=datetime.now(), i=tid)


def delete_task(owner_id: int, tid: int) -> bool:
    if not query("SELECT id FROM tasks WHERE id=:i AND owner_id=:o", i=tid, o=owner_id):
        return False
    execute("DELETE FROM task_steps WHERE task_id=:t", t=tid)
    execute("DELETE FROM artifacts WHERE task_id=:t", t=tid)
    execute("DELETE FROM tasks WHERE id=:i AND owner_id=:o", i=tid, o=owner_id)
    return True


def add_artifact(task_id: int, a: dict) -> int:
    return execute(
        "INSERT INTO artifacts(task_id,kind,title,format,content,size,step_seq,checksum,"
        "created_at) VALUES(:t,:k,:ti,:f,:c,:s,:q,:ck,:d)",
        t=task_id, k=a["kind"], ti=a["title"][:240], f=a["format"], c=a["content"],
        s=int(a.get("size", len(a["content"]))), q=int(a.get("stepSeq", 0)),
        ck=a.get("checksum", ""), d=datetime.now())


def get_artifact(owner_id: int, aid: int) -> dict | None:
    rows = query("SELECT a.* FROM artifacts a JOIN tasks t ON t.id=a.task_id "
                 "WHERE a.id=:i AND t.owner_id=:o", i=aid, o=owner_id)
    return _artifact_to_dict(rows[0], with_content=True) if rows else None


def task_stats(owner_id: int) -> dict:
    rows = query("SELECT status,elapsed_ms,skill_id,skill_name,step_total,step_done,day,"
                 "created_at FROM tasks WHERE owner_id=:o", o=owner_id)
    total = len(rows)
    completed = sum(1 for r in rows if r["status"] == "completed")
    failed = sum(1 for r in rows if r["status"] == "failed")
    finished = completed + failed
    lat = [int(r["elapsed_ms"] or 0) for r in rows if r["status"] == "completed"]
    by_skill: dict[str, int] = {}
    for r in rows:
        by_skill[r["skill_name"] or "通用任务"] = by_skill.get(r["skill_name"] or "通用任务", 0) + 1
    trend = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_rows = [r for r in rows if str(r["day"] or "") == d]
        trend.append({"day": d, "runs": len(day_rows),
                      "errors": sum(1 for x in day_rows
                                    if x["status"] in ("failed", "cancelled"))})
    today_rows = [r for r in rows if str(r["day"] or "") == today()]
    return {
        "tasks": total, "completed": completed, "failed": failed,
        "successRate": round(completed / finished, 4) if finished else 1.0,
        "avgLatencyMs": int(sum(lat) / len(lat)) if lat else 0,
        "tasksToday": len(today_rows),
        "errorsToday": sum(1 for r in today_rows
                           if r["status"] in ("failed", "cancelled")),
        "skills": sorted(by_skill.items(), key=lambda kv: -kv[1]),
        "trend": trend,
    }


# ------------------------------------------------------------------ 知识库
def create_doc(owner_id: int, title: str, content: str, doc_key: str, chunks: int,
               source: str = "manual") -> int:
    return execute("INSERT INTO knowledge_docs(owner_id,title,doc_key,content,chunks,source,"
                   "created_at) VALUES(:o,:t,:k,:c,:n,:s,:d)",
                   o=owner_id, t=title[:200], k=doc_key, c=content, n=chunks, s=source,
                   d=datetime.now())


def list_docs(owner_id: int | None = None) -> list[dict]:
    if owner_id is None:
        rows = query("SELECT * FROM knowledge_docs ORDER BY id DESC")
    else:
        rows = query("SELECT * FROM knowledge_docs WHERE owner_id=:o OR owner_id=0 "
                     "ORDER BY id DESC", o=owner_id)
    return [_doc_to_dict(r) for r in rows]


def _doc_to_dict(r: dict) -> dict:
    content = r["content"] or ""
    return {"id": r["id"], "ownerId": r["owner_id"], "title": r["title"],
            "docKey": r["doc_key"] or "", "chunks": int(r["chunks"] or 0),
            "source": r["source"] or "manual", "size": len(content),
            "preview": content[:120].replace("\n", " "),
            "createdAt": str(r["created_at"] or "")}


def get_doc(did: int) -> dict | None:
    rows = query("SELECT * FROM knowledge_docs WHERE id=:i", i=did)
    if not rows:
        return None
    d = _doc_to_dict(rows[0])
    d["content"] = rows[0]["content"] or ""
    return d


def delete_doc(did: int) -> None:
    execute("DELETE FROM knowledge_docs WHERE id=:i", i=did)


# ------------------------------------------------------------------ 看板
def dashboard_overview(user_id: int) -> dict:
    stats = task_stats(user_id)
    docs_total = scalar("SELECT COUNT(*) FROM knowledge_docs") or 0
    chunks_total = scalar("SELECT COALESCE(SUM(chunks),0) FROM knowledge_docs") or 0
    artifacts_total = scalar("SELECT COUNT(*) FROM artifacts a JOIN tasks t "
                             "ON t.id=a.task_id WHERE t.owner_id=:o", o=user_id) or 0
    recent = list_tasks(user_id, 6)
    return {
        "kpis": {
            "tasks": stats["tasks"], "completed": stats["completed"],
            "failed": stats["failed"], "tasksToday": stats["tasksToday"],
            "errorsToday": stats["errorsToday"], "successRate": stats["successRate"],
            "avgLatencyMs": stats["avgLatencyMs"], "artifacts": artifacts_total,
            "docs": docs_total, "chunks": chunks_total,
        },
        "trend": stats["trend"], "skills": stats["skills"],
        "recent": recent,
    }


def seed_demo_task(owner_id: int, goal: str, result: dict, mode: str = "mock") -> int:
    """首次启动写入一条已完成示例任务，界面打开就有交付物可看。"""
    if query("SELECT id FROM tasks WHERE owner_id=:o LIMIT 1", o=owner_id):
        return 0
    plan = result["plan"]
    tid = create_task(owner_id, goal, plan, mode)
    step_done = 0
    for st in result["steps"]:
        rows = query("SELECT id FROM task_steps WHERE task_id=:t AND seq=:q",
                     t=tid, q=st["seq"])
        if rows:
            update_step(rows[0]["id"], {"status": "success", "output": st["summary"],
                                        "elapsedMs": 120, "finishedAt": datetime.now()})
            step_done += 1
    for a in result["artifacts"]:
        add_artifact(tid, a)
    update_task(tid, {"status": "completed", "progress": 100, "stepDone": step_done,
                      "elapsedMs": 860, "summary": plan.get("summary", "")})
    return tid


# ==================================================================== v5 Agent/Session/Message/Automation
# ====================================================================

BUILTIN_AGENTS = [
    {
        "key": "accio", "name": "灵枢助手", "avatar": "🧭",
        "description": "全能型 AI 助手。处理业务调研、写作、分析等各种任务，不确定选哪个时的首选。",
        "prompt": "你是灵枢，一个全能业务 AI 助手。接到目标后，先拆解成清晰的计划，然后多角色协作执行，最终交付结构化结果。",
        "model": "mock", "skill_ids": ["general", "market_research", "content_marketing", "data_organize", "knowledge_qa"],
        "sort": 10,
    },
    {
        "key": "market", "name": "市场调研官", "avatar": "📊",
        "description": "电商运营、行业分析、趋势洞察。预装市场调研与竞品分析能力。",
        "prompt": "你是专业市场调研员，擅长行业扫描、竞品拆解、消费者洞察。",
        "model": "mock", "skill_ids": ["market_research", "competitor_analysis"], "sort": 20,
    },
    {
        "key": "ecommerce", "name": "电商主理人", "avatar": "🛍️",
        "description": "商品选品、主图文案、竞品对比、流量诊断。适配店铺经营场景。",
        "prompt": "你是资深电商运营，擅长选品、内容生产、竞品对比与店铺数据洞察。",
        "model": "mock", "skill_ids": ["market_research", "content_marketing", "competitor_analysis"], "sort": 30,
    },
    {
        "key": "writer", "name": "内容创作手", "avatar": "✍️",
        "description": "文案撰写、小红书/公众号内容、营销活动策划。",
        "prompt": "你是资深内容创作者，擅长种草文案、活动策划、新媒体内容。",
        "model": "mock", "skill_ids": ["content_marketing"], "sort": 40,
    },
    {
        "key": "data", "name": "数据分析师", "avatar": "📈",
        "description": "数据整理、指标对比、趋势分析、洞察提炼。",
        "prompt": "你是数据分析师，擅长从原始数据中发现洞察、对比竞品、提出建议。",
        "model": "mock", "skill_ids": ["data_organize", "market_research"], "sort": 50,
    },
    {
        "key": "qa", "name": "知识问答官", "avatar": "💬",
        "description": "基于团队知识库回答专业问题，引用可追溯来源。",
        "prompt": "你是知识问答官，回答必须引用知识库原文，标注来源。",
        "model": "mock", "skill_ids": ["knowledge_qa"], "sort": 60,
    },
]


def seed_builtin_agents(user_id: int) -> None:
    for a in BUILTIN_AGENTS:
        if query("SELECT id FROM agents WHERE owner_id=:o AND name=:n", o=user_id, n=a["name"]):
            continue
        execute(
            "INSERT INTO agents(owner_id,name,avatar,description,system_prompt,model,skill_ids,"
            "enabled,is_builtin,sort,created_at) "
            "VALUES(:o,:n,:a,:d,:p,:m,:s,1,1,:so,:c)",
            o=user_id, n=a["name"], a=a["avatar"], d=a["description"],
            p=a["prompt"], m=a["model"],
            s=json.dumps(a["skill_ids"], ensure_ascii=False),
            so=a["sort"], c=datetime.now())


def _agent_to_dict(r: dict) -> dict:
    return {
        "id": r["id"], "ownerId": r["owner_id"], "name": r["name"],
        "avatar": r["avatar"] or "🤖", "description": r["description"] or "",
        "systemPrompt": r["system_prompt"] or "", "model": r["model"] or "mock",
        "skillIds": _loads(r["skill_ids"], []), "enabled": bool(r["enabled"]),
        "isBuiltin": bool(r["is_builtin"]), "sort": r["sort"],
        "createdAt": str(r["created_at"] or ""),
    }


def list_agents(owner_id: int) -> list[dict]:
    rows = query("SELECT * FROM agents WHERE owner_id=:o ORDER BY sort,id", o=owner_id)
    return [_agent_to_dict(r) for r in rows]


def get_agent(owner_id: int, aid: int) -> dict | None:
    rows = query("SELECT * FROM agents WHERE id=:i AND owner_id=:o", i=aid, o=owner_id)
    return _agent_to_dict(rows[0]) if rows else None


def create_agent(owner_id: int, d: dict) -> int:
    return execute(
        "INSERT INTO agents(owner_id,name,avatar,description,system_prompt,model,skill_ids,"
        "enabled,is_builtin,sort,created_at) "
        "VALUES(:o,:n,:a,:d,:p,:m,:s,1,0,:so,:c)",
        o=owner_id, n=d["name"], a=d.get("avatar") or "🤖",
        d=d.get("description", ""), p=d.get("systemPrompt", ""),
        m=d.get("model", "mock"), s=json.dumps(d.get("skillIds", []), ensure_ascii=False),
        so=int(d.get("sort", 80)), c=datetime.now())


def update_agent(owner_id: int, aid: int, d: dict) -> None:
    old = get_agent(owner_id, aid)
    if not old:
        return
    m = {**old, **{k: v for k, v in d.items() if v is not None}}
    execute(
        "UPDATE agents SET name=:n,avatar=:a,description=:d,system_prompt=:p,model=:m,"
        "skill_ids=:s,enabled=:e,sort=:so WHERE id=:i AND owner_id=:o",
        n=m["name"], a=m["avatar"], d=m["description"], p=m["systemPrompt"],
        m=m["model"], s=json.dumps(m["skillIds"], ensure_ascii=False),
        e=1 if m["enabled"] else 0, so=int(m["sort"]), i=aid, o=owner_id)


def delete_agent(owner_id: int, aid: int) -> bool:
    a = get_agent(owner_id, aid)
    if not a or a["isBuiltin"]:
        return False
    for s in query("SELECT id FROM sessions WHERE owner_id=:o AND agent_id=:a", o=owner_id, a=aid):
        execute("DELETE FROM messages WHERE session_id=:s", s=s["id"])
    execute("DELETE FROM sessions WHERE owner_id=:o AND agent_id=:a", o=owner_id, a=aid)
    execute("DELETE FROM automations WHERE owner_id=:o AND agent_id=:a", o=owner_id, a=aid)
    execute("DELETE FROM agents WHERE id=:i AND owner_id=:o", i=aid, o=owner_id)
    return True


def list_sessions(owner_id: int, agent_id: int | None = None, limit: int = 50) -> list[dict]:
    sql = "SELECT s.*, a.name AS agent_name, a.avatar AS agent_avatar FROM sessions s "
    sql += "JOIN agents a ON a.id = s.agent_id WHERE s.owner_id=:o"
    params: dict = {"o": owner_id, "n": int(limit)}
    if agent_id is not None:
        sql += " AND s.agent_id=:a"
        params["a"] = agent_id
    sql += " ORDER BY s.updated_at DESC LIMIT :n"
    out = []
    for r in query(sql, **params):
        out.append({
            "id": r["id"], "agentId": r["agent_id"], "agentName": r["agent_name"],
            "agentAvatar": r["agent_avatar"], "title": r["title"],
            "lastMessage": r["last_message"] or "",
            "updatedAt": str(r["updated_at"] or ""),
        })
    return out


def create_session(owner_id: int, agent_id: int, title: str = "新对话") -> int:
    return execute(
        "INSERT INTO sessions(owner_id,agent_id,title,last_message,updated_at) "
        "VALUES(:o,:a,:t,'',:u)",
        o=owner_id, a=agent_id, t=(title or "新对话")[:120], u=datetime.now())


def rename_session(owner_id: int, sid: int, title: str) -> None:
    execute("UPDATE sessions SET title=:t,updated_at=:u WHERE id=:i AND owner_id=:o",
            t=title[:120], u=datetime.now(), i=sid, o=owner_id)


def delete_session(owner_id: int, sid: int) -> bool:
    if not query("SELECT id FROM sessions WHERE id=:i AND owner_id=:o", i=sid, o=owner_id):
        return False
    execute("DELETE FROM messages WHERE session_id=:s", s=sid)
    execute("DELETE FROM sessions WHERE id=:i AND owner_id=:o", i=sid, o=owner_id)
    return True


def session_exists(owner_id: int, sid: int) -> bool:
    return bool(query("SELECT id FROM sessions WHERE id=:i AND owner_id=:o", i=sid, o=owner_id))


def get_session(owner_id: int, sid: int) -> dict | None:
    rows = query("SELECT * FROM sessions WHERE id=:i AND owner_id=:o", i=sid, o=owner_id)
    return rows[0] if rows else None


def _message_to_dict(r: dict) -> dict:
    return {
        "id": r["id"], "sessionId": r["session_id"], "role": r["role"],
        "content": r["content"] or "", "msgType": r["msg_type"],
        "stepNo": r["step_no"], "data": _loads(r["data"], {}),
        "status": r["status"], "taskId": r["task_id"],
        "createdAt": str(r["created_at"] or ""),
    }


def list_messages(session_id: int) -> list[dict]:
    return [_message_to_dict(m) for m in
            query("SELECT * FROM messages WHERE session_id=:s ORDER BY id", s=session_id)]


def add_message(session_id: int, role: str, content: str, msg_type: str = "text",
                step_no: int = 0, data: dict | None = None, status: str = "success",
                task_id: int | None = None) -> int:
    mid = execute(
        "INSERT INTO messages(session_id,role,content,msg_type,step_no,data,status,task_id) "
        "VALUES(:s,:r,:c,:t,:sn,:d,:st,:tk)",
        s=session_id, r=role, c=content or "", t=msg_type, sn=step_no,
        d=json.dumps(data or {}, ensure_ascii=False, default=str), st=status, tk=task_id)
    preview = (content or "").replace("\n", " ")[:200]
    execute("UPDATE sessions SET last_message=:lm,updated_at=:u WHERE id=:s",
            lm=preview, u=datetime.now(), s=session_id)
    return mid


def list_automations(owner_id: int) -> list[dict]:
    sql = ("SELECT a.*, ag.name AS agent_name, ag.avatar AS agent_avatar "
           "FROM automations a JOIN agents ag ON ag.id=a.agent_id "
           "WHERE a.owner_id=:o ORDER BY a.id DESC")
    out = []
    for r in query(sql, o=owner_id):
        out.append({
            "id": r["id"], "agentId": r["agent_id"],
            "agentName": r["agent_name"], "agentAvatar": r["agent_avatar"],
            "name": r["name"], "cronExpr": r["cron_expr"],
            "goal": r["goal"], "enabled": bool(r["enabled"]),
            "lastRunAt": str(r["last_run_at"] or ""),
            "nextRunAt": str(r["next_run_at"] or ""),
            "createdAt": str(r["created_at"] or ""),
        })
    return out


def create_automation(owner_id: int, agent_id: int, name: str, cron_expr: str, goal: str) -> int:
    return execute(
        "INSERT INTO automations(owner_id,agent_id,name,cron_expr,goal,enabled,created_at) "
        "VALUES(:o,:a,:n,:c,:g,1,:d)",
        o=owner_id, a=agent_id, n=name[:64], c=cron_expr[:40], g=goal, d=datetime.now())


def update_automation(owner_id: int, aid: int, d: dict) -> None:
    fields, params = [], {"i": aid, "o": owner_id}
    mapping = {"name": "name", "cronExpr": "cron_expr", "goal": "goal",
               "agentId": "agent_id"}
    for k, col in mapping.items():
        if k in d and d[k] is not None:
            fields.append(f"{col}=:{k}")
            params[k] = d[k]
    if "enabled" in d and d["enabled"] is not None:
        fields.append("enabled=:e")
        params["e"] = 1 if d["enabled"] else 0
    if not fields:
        return
    execute(f"UPDATE automations SET {', '.join(fields)} WHERE id=:i AND owner_id=:o", **params)


def delete_automation(owner_id: int, aid: int) -> bool:
    if not query("SELECT id FROM automations WHERE id=:i AND owner_id=:o", i=aid, o=owner_id):
        return False
    execute("DELETE FROM automations WHERE id=:i AND owner_id=:o", i=aid, o=owner_id)
    return True


# ---------- scheduler helpers ----------

def list_automations_all_enabled() -> list[dict]:
    """列出所有 enabled 的定时任务（scheduler 启动时加载用）。"""
    out = []
    for r in query("SELECT * FROM automations WHERE enabled=1"):
        out.append({
            "id": r["id"], "owner_id": r["owner_id"], "agent_id": r["agent_id"],
            "name": r["name"], "cron_expr": r["cron_expr"], "goal": r["goal"],
            "enabled": bool(r["enabled"]),
        })
    return out


def get_automation(aid: int) -> dict | None:
    rows = query("SELECT * FROM automations WHERE id=:i", i=aid)
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r["id"], "owner_id": r["owner_id"], "agent_id": r["agent_id"],
        "name": r["name"], "cron_expr": r["cron_expr"], "goal": r["goal"],
        "enabled": bool(r["enabled"]),
    }


def update_automation_last(aid: int, dt_str: str) -> None:
    execute("UPDATE automations SET last_run_at=:d WHERE id=:i", d=dt_str, i=aid)


def update_automation_next(aid: int, dt_obj) -> None:
    """接受 datetime 或 datetime string。"""
    from datetime import datetime
    if hasattr(dt_obj, "strftime"):
        s = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    else:
        s = str(dt_obj)[:19]
    execute("UPDATE automations SET next_run_at=:d WHERE id=:i", d=s, i=aid)
