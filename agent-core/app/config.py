"""统一配置：敏感信息一律走环境变量，代码里不出现任何 API Key 字面量。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """轻量加载 agent-core/.env；系统环境变量优先，不覆盖已有值。

    不引入 python-dotenv 依赖，CI / 零配置环境同样可用。
    """
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# ---- DeepSeek（OpenAI 兼容协议）----
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")

# mock=确定性可复现；live=真实 DeepSeek；auto=有 Key 走 live 否则 mock
AGENT_MODE = _env("AGENT_MODE", "auto")

# ---- Redis（多轮会话记忆 / 执行结果缓存）----
REDIS_HOST = _env("REDIS_HOST", "localhost")
REDIS_PORT = int(_env("REDIS_PORT", "6379"))
REDIS_DB = int(_env("REDIS_DB", "0"))
REDIS_PASSWORD = _env("REDIS_PASSWORD", "") or None
CACHE_TTL = int(_env("CACHE_TTL", "600"))

# ---- Chroma 向量库 ----
CHROMA_DIR = str(ROOT / "data" / "chroma")
COLLECTION = _env("CHROMA_COLLECTION", "nexus_knowledge")
EMBED_DIM = 384
RAG_TOP_K = int(_env("RAG_TOP_K", "3"))

# ---- 编排 ----
MAX_STEPS = int(_env("MAX_STEPS", "6"))   # LangGraph 循环上限，防死循环
API_HOST = _env("API_HOST", "127.0.0.1")
API_PORT = int(_env("API_PORT", "8000"))  # 单服务统一端口：业务接口 + Agent 核心接口

KNOWLEDGE_DIR = ROOT / "knowledge" / "docs"

# ---- MySQL 3307（业务数据持久化）----
MYSQL_HOST = _env("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(_env("MYSQL_PORT", "3307"))
MYSQL_USER = _env("MYSQL_USER", "root")
MYSQL_PASSWORD = _env("MYSQL_PASSWORD", "123456")
MYSQL_DB = _env("MYSQL_DB", "nexus_agent")
# MySQL 不可用时自动降级 SQLite（CI / 零配置演示用）；教程默认走 MySQL
DB_FALLBACK_SQLITE = _env("DB_FALLBACK_SQLITE", "1") == "1"
SQLITE_PATH = ROOT / "data" / "nexus.db"

# ---- JWT 鉴权 ----
# 开发默认值仅用于本机；部署时必须通过环境变量 JWT_SECRET 覆盖
JWT_SECRET = _env("JWT_SECRET", "agenthub-local-dev-secret-change-me")
JWT_TTL = int(_env("JWT_TTL", "86400"))   # Token 有效期（秒），默认 24 小时


def deepseek_enabled() -> bool:
    return bool(DEEPSEEK_API_KEY) and not DEEPSEEK_API_KEY.startswith("sk-PLACEHOLDER")
