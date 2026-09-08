"""mcp_server 资源 / 提示词 / 工具注册的本地测试（不起服务进程）。

覆盖 Stage 5 Task 2 交付：
- 5 个 MCP 工具按名称注册（Task 1 行为回归）。
- rag://knowledge-bases 资源存在，内容覆盖三个知识库名。
- interviewer_persona / coach_persona 两个提示词注册且可渲染。
- call_tool("retrieve_role_knowledge", ...) 本地往返返回 list
  （hermetic：monkeypatch mcp_server.server.SessionLocal 到临时 SQLite
  引擎并 create_all，不触碰开发库；断言类型不断言内容，空列表可接受）。
"""

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_server import server as mcp_server_module  # noqa: E402
from mcp_server.server import mcp  # noqa: E402

EXPECTED_TOOL_NAMES = [
    "draft_interview_question",
    "generate_interview_report",
    "retrieve_candidate_profile",
    "retrieve_question_bank",
    "retrieve_role_knowledge",
]

KNOWLEDGE_BASE_NAMES = ["role_knowledge", "question_bank", "candidate_memory"]

PERSONA_PROMPT_NAMES = ["interviewer_persona", "coach_persona"]


def test_list_tools_exposes_five_tools() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert sorted(tool.name for tool in tools) == EXPECTED_TOOL_NAMES


def test_knowledge_bases_resource_covers_all_three_knowledge_bases() -> None:
    resources = asyncio.run(mcp.list_resources())
    uris = [str(resource.uri) for resource in resources]

    assert "rag://knowledge-bases" in uris

    contents = asyncio.run(mcp.read_resource("rag://knowledge-bases"))
    text = "".join(str(part.content) for part in contents)
    for name in KNOWLEDGE_BASE_NAMES:
        assert name in text


def test_list_prompts_contains_both_personas() -> None:
    prompts = asyncio.run(mcp.list_prompts())
    names = {prompt.name for prompt in prompts}

    assert set(PERSONA_PROMPT_NAMES) <= names
    for prompt_name in PERSONA_PROMPT_NAMES:
        rendered = asyncio.run(mcp.get_prompt(prompt_name))
        assert rendered.messages
        message_text = "".join(
            part.content.text for part in rendered.messages if hasattr(part.content, "text")
        )
        assert message_text.strip()


def test_call_tool_retrieve_role_knowledge_returns_list(monkeypatch, tmp_path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend_python import db_models  # noqa: F401  # 确保所有模型注册到 Base.metadata
    from backend_python.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'mcp_server_test.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(
        mcp_server_module,
        "SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=engine),
    )

    result = asyncio.run(mcp.call_tool("retrieve_role_knowledge", {"query": "RAG", "limit": 2}))

    assert result.is_error is False
    # v2 SDK 将 list 返回值包裹为 {"result": [...]}（structured_content）。
    assert isinstance(result.structured_content, dict)
    assert isinstance(result.structured_content.get("result"), list)
