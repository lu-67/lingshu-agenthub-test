"""
灵枢 AgentHub · 任务型智能体工作台
====================================
单服务 FastAPI（:8000）：一个进程同时提供前端所需的全部接口。

  /api/auth*          注册 / 登录 / 当前用户 / 图形验证码
  /api/agents*        智能体 CRUD
  /api/sessions*      会话管理 + 发送目标 → 自动执行
  /api/automations*   定时任务 CRUD（同步 APScheduler）
  /api/artifacts/*/download  交付物下载
  /api/admin*         管理端（用户、数据库、调度器状态）
  /health             健康检查

技术栈：FastAPI + 多角色编排引擎 + Chroma RAG + DeepSeek(可选) + SQLite/MySQL
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, chat, config, db, engine, llm, memory, ops, rag, security

DEMO_GOAL = "调研 2026 年国内宠物智能硬件市场，输出机会点与进入建议"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(security.hash_password)
    n = rag.load_seed_docs()
    demo = 0
    for row in db.list_users():
        if row["username"] not in ("tester", "admin"):
            continue
        if db.scalar("SELECT COUNT(*) FROM tasks WHERE owner_id=:o", o=row["id"]) == 0:
            result = engine.run_plan(DEMO_GOAL)
            demo += int(bool(db.seed_demo_task(row["id"], DEMO_GOAL, result)))
    print(f"[startup] RAG seed docs ingested: {n}, total chunks: {rag.count()}", flush=True)
    print(f"[startup] demo tasks seeded: {demo}", flush=True)
    print(f"[startup] DB backend: {db.backend()}", flush=True)
    print(f"[startup] Redis available: {memory.available()}", flush=True)
    print(f"[startup] DeepSeek enabled: {config.deepseek_enabled()}", flush=True)
    print(f"[startup] AgentHub ready on :{config.API_PORT}", flush=True)
    # 启动定时任务调度器
    try:
        from . import scheduler
        if scheduler.init():
            print(f"[startup] Scheduler OK, automations loaded", flush=True)
        else:
            print(f"[startup] Scheduler SKIPPED (APScheduler not installed)", flush=True)
    except Exception as e:
        print(f"[startup] Scheduler FAIL: {e}", flush=True)
    yield
    # 关闭调度器
    try:
        from . import scheduler
        scheduler.shutdown()
    except Exception:
        pass
    print(f"[shutdown] done", flush=True)


app = FastAPI(
    title="灵枢 AgentHub · 任务型智能体工作台",
    version="0.1.0",
    description="一句话目标 → 智能体自动规划 → 执行 → 自然语言回答"
                " | FastAPI + Chroma RAG + 多角色编排引擎",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(ops.router)


@app.get("/health")
def health():
    """健康检查：Swagger / JMeter / pytest 用它判断服务是否就绪。"""
    return {
        "status": "ok",
        "architecture": "single-service-fastapi",
        "engine": "multi-agent-planner",
        "db_backend": db.backend(), "mysql": db.backend() == "mysql",
        "redis": memory.available(), "deepseek": config.deepseek_enabled(),
        "chroma_docs": rag.count(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.API_HOST, port=config.API_PORT, reload=False)
