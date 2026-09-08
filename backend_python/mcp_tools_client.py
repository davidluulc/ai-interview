"""MCP 客户端适配层：把 MCP server 的三个检索工具适配成 graph_v3 的 tool_fns 约定。

设计要点（Stage 5 Task 3）：
- ``call_tool_with_fallback`` 是唯一的 MCP 调用通道。``client_factory`` 的约定是
  ``factory() -> async CM(yield ClientSession)``；真实工厂由接线方用
  ``mcp.client.streamable_http.streamable_http_client`` + ``mcp.ClientSession`` +
  ``initialize`` 组装（SDK 2.2.0 已核对：客户端函数名是 ``streamable_http_client``，
  不是 v1 风格的 ``streamablehttp_client``）。
- MCP 侧任何异常（连接失败/协议错误/超时/工具 is_error）→ ``logger.warning`` 后
  回退 ``in_process_fn``（应用内检索函数），``transport`` 字段区分实际链路：
  ``"mcp"`` / ``"mcp-fallback"`` / ``"in-process"``。
- 结构化解包：SDK 服务端把非 dict 返回值（如 ``list[dict]``）包装成
  ``{"result": [...]}`` 的 structured content；客户端优先取
  ``result.structured_content["result"]``，缺失时回退解析 content 文本块的 JSON
  （服务端对 list 返回的 unstructured content 就是整体 JSON dump）。
- sanitize：MCP 返回进入 graph 前统一去控制字符（保留 ``\\n``/``\\t``）并截断
  （默认 4000 字符 + ``…[truncated]`` 标记），列表截到 20 条，防止超长内容
  拖垮 agent 上下文。in-process 链路返回应用原生结果、不经此 sanitize
  （与 agent_runtime 既有 tool_fns 行为一致）。

graph_v3 工具约定（同 ``agent_runtime._build_langgraph_v3_tool_fns``）::

    fn(profile: dict, next_stage: str = "", tool_query: str = "") -> list[dict]

检索词 tool_query 优先、next_stage 兜底；闭包为同步函数（内部 ``asyncio.run``
驱动，与 retrieval_service 的既有模式一致）。in-process 回退使用应用自身检索
（db=None/user_id=None 默认：role/question 走静态语料兜底，memory 临时开
SessionLocal——与 agent_runtime 闭包同形）。闭包刻意保持薄：trace/摘要由
graph_v3 的 tools 节点自行构建。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_CHARS = 4000
MAX_ITEMS = 20
TRUNCATION_MARKER = "…[truncated]"


def sanitize_mcp_content(text: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """去控制字符（保留 \n\t）并按 max_chars 截断，超长追加 …[truncated] 标记。"""
    cleaned = "".join(ch for ch in str(text) if ch in "\n\t" or ch.isprintable())
    if len(cleaned) > max_chars:
        return cleaned[:max_chars] + TRUNCATION_MARKER
    return cleaned


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_mcp_content(value)
    if isinstance(value, dict):
        return {key: _sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value[:MAX_ITEMS]]
    return value


def _parse_content_blocks(content_blocks: Any) -> Any:
    """无 structured_content 时的兜底：拼接文本块并尝试按 JSON 解析。"""
    texts: list[str] = []
    for block in content_blocks or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            texts.append(text)
    for text in texts:
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            continue
    return "\n".join(texts)


async def _await_or_call(fn: Callable[[], Any]) -> Any:
    value = fn()
    if inspect.isawaitable(value):
        value = await value
    return value


async def call_tool_with_fallback(
    tool: str,
    payload: dict,
    *,
    in_process_fn: Callable[[], Any],
    client_factory: Callable[[], Any] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """经 MCP 调用工具，失败/超时/无工厂时回退 in_process_fn。

    返回 ``{"result": Any, "transport": "mcp" | "mcp-fallback" | "in-process"}``；
    MCP 成功路径的 result 已整体 sanitize（字符串截断、列表封顶 MAX_ITEMS）。
    开关（是否启用 MCP）由调用方处理：未提供 client_factory 即视为关闭。
    """
    if client_factory is None:
        return {"result": await _await_or_call(in_process_fn), "transport": "in-process"}
    try:
        async with client_factory() as session:
            result = await asyncio.wait_for(
                session.call_tool(tool, payload), timeout=timeout_seconds
            )
        if getattr(result, "is_error", False):
            raise ValueError(f"MCP tool {tool} returned an is_error result")
        structured = getattr(result, "structured_content", None)
        if isinstance(structured, dict) and "result" in structured:
            data = structured["result"]
        else:
            data = _parse_content_blocks(getattr(result, "content", None))
        return {"result": _sanitize_payload(data), "transport": "mcp"}
    except Exception as exc:
        logger.warning("MCP 工具 %s 调用失败，回退 in-process：%s", tool, exc)
        return {"result": await _await_or_call(in_process_fn), "transport": "mcp-fallback"}


def build_streamable_http_factory(
    url: str, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> Callable[[], Any]:
    """组装真实 streamable-http 工厂，形状满足 client_factory 约定：
    ``factory() -> async CM(yield ClientSession)``。

    连接（``streamable_http_client(url)``）→ ``ClientSession`` 进入 →
    ``initialize()`` 全部在 ``asyncio.wait_for(timeout_seconds)`` 预算内完成
    （``call_tool_with_fallback`` 只包 call_tool 调用本身，不包连接握手）；
    超时/连接失败抛出的异常由 ``call_tool_with_fallback`` 捕获并回退
    in-process。SDK 2.2.0 客户端入口是
    ``mcp.client.streamable_http.streamable_http_client``（惰性导入，便于
    测试替身按源模块打桩）。
    """

    async def _open() -> tuple[AsyncExitStack, Any]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        stack = AsyncExitStack()
        try:
            streams = await stack.enter_async_context(streamable_http_client(url))
            session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
        except BaseException:
            await stack.aclose()
            raise
        return stack, session

    @asynccontextmanager
    async def _session() -> Any:
        stack, session = await asyncio.wait_for(_open(), timeout=timeout_seconds)
        try:
            yield session
        finally:
            await stack.aclose()

    def factory() -> Any:
        return _session()

    return factory


def build_mcp_tool_fns(client_factory: Callable[[], Any] | None) -> dict[str, Callable[..., list[dict[str, Any]]]]:
    """把三个 MCP 检索工具包装成 graph_v3 的 tool_fns（键与 agent_runtime 一致）。

    键 → MCP 工具名映射：retrieve_candidate_memory 键对应服务端的
    retrieve_candidate_profile 工具（服务端以 KB 实名命名，graph 侧沿用
    agent_runtime 的记忆检索键名）。payload 固定 ``{"query": ..., "limit": 3}``。
    """

    def _query(next_stage: str, tool_query: str) -> str:
        return str(tool_query or next_stage or "")

    def retrieve_role_knowledge(
        profile: dict[str, Any], next_stage: str = "", tool_query: str = ""
    ) -> list[dict[str, Any]]:
        query = _query(next_stage, tool_query)
        outcome = asyncio.run(
            call_tool_with_fallback(
                "retrieve_role_knowledge",
                {"query": query, "limit": 3},
                in_process_fn=_in_process_role(profile, query),
                client_factory=client_factory,
            )
        )
        return outcome["result"]

    def retrieve_question_bank(
        profile: dict[str, Any], next_stage: str = "", tool_query: str = ""
    ) -> list[dict[str, Any]]:
        query = _query(next_stage, tool_query)
        outcome = asyncio.run(
            call_tool_with_fallback(
                "retrieve_question_bank",
                {"query": query, "limit": 3},
                in_process_fn=_in_process_question(profile, query),
                client_factory=client_factory,
            )
        )
        return outcome["result"]

    def retrieve_candidate_memory(
        profile: dict[str, Any], next_stage: str = "", tool_query: str = ""
    ) -> list[dict[str, Any]]:
        query = _query(next_stage, tool_query)
        outcome = asyncio.run(
            call_tool_with_fallback(
                "retrieve_candidate_profile",
                {"query": query, "limit": 3},
                in_process_fn=_in_process_memory(profile),
                client_factory=client_factory,
            )
        )
        return outcome["result"]

    def _in_process_role(profile: dict[str, Any], query: str) -> Callable[[], list[dict[str, Any]]]:
        def _run() -> list[dict[str, Any]]:
            from .rag import retrieve_role_context

            return retrieve_role_context(profile, query, limit=3, db=None, user_id=None)

        return _run

    def _in_process_question(profile: dict[str, Any], query: str) -> Callable[[], list[dict[str, Any]]]:
        def _run() -> list[dict[str, Any]]:
            from .question_rag import retrieve_questions

            return retrieve_questions(profile, query, limit=3, db=None, user_id=None)

        return _run

    def _in_process_memory(profile: dict[str, Any]) -> Callable[[], list[dict[str, Any]]]:
        def _run() -> list[dict[str, Any]]:
            from .candidate_memory import retrieve_candidate_memory as retrieve_memory
            from .database import SessionLocal

            session = SessionLocal()
            try:
                return retrieve_memory(
                    session, profile, limit=3, user_id=None, application_profile_id=None
                )
            finally:
                session.close()

        return _run

    return {
        "retrieve_role_knowledge": retrieve_role_knowledge,
        "retrieve_question_bank": retrieve_question_bank,
        "retrieve_candidate_memory": retrieve_candidate_memory,
    }
