import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")
QWEN_VISION_MODEL = os.getenv("QWEN_VISION_MODEL", "qwen-vl-plus")
DASHSCOPE_EMBEDDING_MODEL = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
DASHSCOPE_RERANK_MODEL = os.getenv("DASHSCOPE_RERANK_MODEL", "qwen3-rerank")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


REDIS_ENABLED = env_bool("REDIS_ENABLED", False)
AUTO_INIT_DB = env_bool("AUTO_INIT_DB", True)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
VECTOR_SEARCH_BACKEND = os.getenv("VECTOR_SEARCH_BACKEND", "sqlite").strip().lower()
HYBRID_FUSION_MODE = os.getenv("HYBRID_FUSION_MODE", "weighted").strip().lower()
try:
    EMBEDDING_DIMENSIONS_INT = int(os.getenv("EMBEDDING_DIMENSIONS") or 2048)
except (TypeError, ValueError):
    # 垃圾值兜底为 2048（迁移落地的 vector(2048) 列宽），避免 import 期崩溃。
    EMBEDDING_DIMENSIONS_INT = 2048


def structured_output_enabled() -> bool:
    """LLM_STRUCTURED_OUTPUT=chain（默认）| legacy。运行时动态读取，便于灰度与回滚。"""
    value = os.getenv("LLM_STRUCTURED_OUTPUT", "chain").strip().lower()
    return value not in {"legacy", "off", "0", "false"}


def mcp_tools_enabled() -> bool:
    """MCP_TOOLS_ENABLED（默认关闭）。运行时动态读取，便于灰度与回滚。

    取值 1/true/on/yes（大小写不敏感）视为开启；默认 off——未显式配置时
    langgraph_agent_v3 分派保持应用内检索，不依赖 MCP server 进程。
    """
    return env_bool("MCP_TOOLS_ENABLED", False)


# langgraph_agent_v3 启用 MCP 检索工具时连接的 streamable-http 端点；
# compose 部署经 app 服务环境覆盖为 http://mcp:8000/mcp。
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp").strip()
