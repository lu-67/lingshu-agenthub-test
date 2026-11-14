"""一键启动 Agent 核心层：python run_server.py （不依赖当前工作目录）"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import uvicorn
from app import config

if __name__ == "__main__":
    print(f"[AgentHub Core] http://{config.API_HOST}:{config.API_PORT}  docs=/docs", flush=True)
    uvicorn.run("app.main:app", host=config.API_HOST, port=config.API_PORT,
                log_level="info", access_log=True)
