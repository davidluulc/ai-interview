"""backend_python.mcp_tools_client 客户端适配层的 fake 驱动测试（不起服务、不联网）。

覆盖 Stage 5 Task 3 交付：
- sanitize_mcp_content：去控制字符（保留 \\n\\t）、4000 截断加 …[truncated] 标记。
- call_tool_with_fallback：fake client（返回带 structured_content 的结果对象）走通 →
  解包 structured_content["result"] + 逐字段 sanitize，transport="mcp"，in_process 不被调用。
- call_tool_with_fallback：工厂 __aenter__ 抛错 / call_tool 抛错 / call_tool 超时 /
  is_error 结果 → 回退 in_process_fn，transport="mcp-fallback"。
- client_factory=None → 直接 in-process（sync / async in_process_fn 都支持）。
- build_mcp_tool_fns：graph_v3 约定的三个检索键 → 正确的 MCP 工具名与
  payload {"query": ..., "limit": 3}（tool_query 优先，next_stage 兜底）。
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend_python.mcp_tools_client import (  # noqa: E402
    build_mcp_tool_fns,
    call_tool_with_fallback,
    sanitize_mcp_content,
)

TRUNCATION_MARKER = "…[truncated]"


class FakeTextBlock:
    """Mimics mcp.types.TextContent：只暴露 call_tool_with_fallback 依赖的 text。"""

    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class FakeCallToolResult:
    """Mimics mcp.types.CallToolResult：content / structured_content / is_error。"""

    def __init__(self, *, structured_content=None, content=None, is_error=False) -> None:
        self.structured_content = structured_content
        self.content = list(content or [])
        self.is_error = is_error


class FakeSession:
    """Mimics ClientSession：只实现 call_tool，记录调用供断言。"""

    def __init__(self, handler) -> None:
        self._handler = handler
        self.calls: list[dict] = []

    async def call_tool(self, name, arguments=None, **kwargs):
        self.calls.append({"name": name, "arguments": dict(arguments or {})})
        result = self._handler(name, arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return result


def make_client_factory(session: FakeSession):
    """返回 () -> async CM(yield session) 形状的 client_factory（与真实工厂同约定）。"""

    def factory():
        @asynccontextmanager
        async def _ctx():
            yield session

        return _ctx()

    return factory


# ---------------------------------------------------------------------------
# 1. sanitize_mcp_content
# ---------------------------------------------------------------------------


def test_sanitize_strips_control_chars_but_keeps_newline_and_tab() -> None:
    raw = "a\x00b\x1fc\r\nd\te\x7f"
    assert sanitize_mcp_content(raw) == "abc\nd\te"


def test_sanitize_truncates_at_4000_with_marker() -> None:
    out = sanitize_mcp_content("x" * 5000)
    assert out == "x" * 4000 + TRUNCATION_MARKER
    assert len(out) == 4000 + len(TRUNCATION_MARKER)
    # 恰好 4000 不截断
    assert sanitize_mcp_content("y" * 4000) == "y" * 4000


def test_sanitize_custom_max_chars_and_short_text_untouched() -> None:
    assert sanitize_mcp_content("abcdef", max_chars=3) == "abc" + TRUNCATION_MARKER
    assert sanitize_mcp_content("short\nmulti\tline") == "short\nmulti\tline"


# ---------------------------------------------------------------------------
# 2. call_tool_with_fallback：MCP 成功路径
# ---------------------------------------------------------------------------


def test_mcp_success_unwraps_result_sanitizes_and_skips_in_process() -> None:
    async def run() -> None:
        session = FakeSession(
            lambda name, arguments: _ok({"result": [{"title": "x" * 5000, "content": "y"}]})
        )
        in_process_calls: list[str] = []

        def in_process():
            in_process_calls.append("called")
            return [{"title": "fallback", "content": ""}]

        outcome = await call_tool_with_fallback(
            "retrieve_role_knowledge",
            {"query": "Redis", "limit": 3},
            in_process_fn=in_process,
            client_factory=make_client_factory(session),
        )
        assert outcome["transport"] == "mcp"
        assert outcome["result"] == [{"title": "x" * 4000 + TRUNCATION_MARKER, "content": "y"}]
        assert in_process_calls == []
        assert session.calls == [
            {"name": "retrieve_role_knowledge", "arguments": {"query": "Redis", "limit": 3}}
        ]

    asyncio.run(run())


def test_mcp_success_caps_list_at_20_and_sanitizes_nested_dicts() -> None:
    items = [{"title": "t" * 4500, "meta": {"note": "n" * 4500}}] + [
        {"i": i} for i in range(30)
    ]

    async def run() -> None:
        session = FakeSession(lambda name, arguments: _ok({"result": items}))
        outcome = await call_tool_with_fallback(
            "retrieve_question_bank",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [],
            client_factory=make_client_factory(session),
        )
        assert outcome["transport"] == "mcp"
        assert len(outcome["result"]) == 20
        first = outcome["result"][0]
        assert first["title"] == "t" * 4000 + TRUNCATION_MARKER
        assert first["meta"]["note"] == "n" * 4000 + TRUNCATION_MARKER
        assert outcome["result"][1]["i"] == 0  # 非字符串字段原样保留（items[1] 即 {"i": 0}）

    asyncio.run(run())


def test_mcp_success_without_structured_content_parses_text_content_json() -> None:
    raw_hits = [{"title": "z" * 5000, "content": "c"}]

    async def run() -> None:
        session = FakeSession(
            lambda name, arguments: FakeCallToolResult(
                content=[FakeTextBlock(json.dumps(raw_hits, ensure_ascii=False))]
            )
        )
        outcome = await call_tool_with_fallback(
            "retrieve_role_knowledge",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [],
            client_factory=make_client_factory(session),
        )
        assert outcome["transport"] == "mcp"
        assert outcome["result"] == [{"title": "z" * 4000 + TRUNCATION_MARKER, "content": "c"}]

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 3. call_tool_with_fallback：失败/超时 → in-process 回退
# ---------------------------------------------------------------------------


def test_call_tool_raises_falls_back_to_in_process() -> None:
    async def run() -> None:
        def boom(name, arguments):
            raise RuntimeError("tool crashed")

        session = FakeSession(boom)

        async def in_process():
            return [{"title": "inproc", "content": ""}]

        outcome = await call_tool_with_fallback(
            "retrieve_role_knowledge",
            {"query": "q", "limit": 3},
            in_process_fn=in_process,
            client_factory=make_client_factory(session),
        )
        assert outcome == {"result": [{"title": "inproc", "content": ""}], "transport": "mcp-fallback"}

    asyncio.run(run())


def test_call_tool_timeout_falls_back_to_in_process() -> None:
    async def run() -> None:
        async def slow(name, arguments):
            await asyncio.sleep(999)
            return _ok({"result": []})

        session = FakeSession(slow)

        outcome = await call_tool_with_fallback(
            "retrieve_question_bank",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [{"title": "inproc", "content": ""}],
            client_factory=make_client_factory(session),
            timeout_seconds=0.05,
        )
        assert outcome == {"result": [{"title": "inproc", "content": ""}], "transport": "mcp-fallback"}

    asyncio.run(run())


def test_factory_enter_raises_falls_back_to_in_process() -> None:
    async def run() -> None:
        def broken_factory():
            @asynccontextmanager
            async def _ctx():
                raise RuntimeError("connect refused")
                yield  # pragma: no cover

            return _ctx()

        outcome = await call_tool_with_fallback(
            "retrieve_candidate_profile",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [],
            client_factory=broken_factory,
        )
        assert outcome == {"result": [], "transport": "mcp-fallback"}

    asyncio.run(run())


def test_is_error_result_falls_back_to_in_process() -> None:
    async def run() -> None:
        session = FakeSession(
            lambda name, arguments: FakeCallToolResult(
                content=[FakeTextBlock("tool exploded")], is_error=True
            )
        )
        outcome = await call_tool_with_fallback(
            "retrieve_role_knowledge",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [{"title": "inproc", "content": ""}],
            client_factory=make_client_factory(session),
        )
        assert outcome == {"result": [{"title": "inproc", "content": ""}], "transport": "mcp-fallback"}

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 4. client_factory=None → 直接 in-process
# ---------------------------------------------------------------------------


def test_none_factory_runs_sync_in_process_directly() -> None:
    async def run() -> None:
        outcome = await call_tool_with_fallback(
            "retrieve_role_knowledge",
            {"query": "q", "limit": 3},
            in_process_fn=lambda: [{"a": 1}],
            client_factory=None,
        )
        assert outcome == {"result": [{"a": 1}], "transport": "in-process"}

    asyncio.run(run())


def test_none_factory_awaits_async_in_process() -> None:
    async def run() -> None:
        async def in_process():
            return [{"a": 2}]

        outcome = await call_tool_with_fallback(
            "retrieve_question_bank",
            {"query": "q", "limit": 3},
            in_process_fn=in_process,
            client_factory=None,
        )
        assert outcome == {"result": [{"a": 2}], "transport": "in-process"}

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 5. build_mcp_tool_fns
# ---------------------------------------------------------------------------


def test_build_mcp_tool_fns_maps_graph_v3_keys_to_mcp_tools() -> None:
    session = FakeSession(lambda name, arguments: _ok({"result": [{"title": "t", "content": "c"}]}))
    fns = build_mcp_tool_fns(make_client_factory(session))

    assert set(fns) == {
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    }

    role_hits = fns["retrieve_role_knowledge"](
        profile={"role": "后端"}, next_stage="基础", tool_query="Redis 持久化"
    )
    question_hits = fns["retrieve_question_bank"](profile={}, next_stage="", tool_query="缓存一致性")
    memory_hits = fns["retrieve_candidate_memory"](profile={}, next_stage="项目深挖", tool_query="")

    assert role_hits == [{"title": "t", "content": "c"}]
    assert question_hits == [{"title": "t", "content": "c"}]
    assert memory_hits == [{"title": "t", "content": "c"}]

    assert [call["name"] for call in session.calls] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_profile",
    ]
    assert session.calls[0]["arguments"] == {"query": "Redis 持久化", "limit": 3}
    assert session.calls[1]["arguments"] == {"query": "缓存一致性", "limit": 3}
    # tool_query 为空时回退 next_stage
    assert session.calls[2]["arguments"] == {"query": "项目深挖", "limit": 3}


def test_build_mcp_tool_fns_with_none_factory_falls_back_in_process() -> None:
    """client_factory=None（MCP 关闭）时三个闭包仍可用：走 in-process 回退。

    role/question 以 db=None/user_id=None 命中静态语料兜底；memory 闭包临时开
    SessionLocal 只做只读 SELECT（与 agent_runtime 闭包同形，仓内测试惯例允许
    触及本地 dev sqlite，见 tests/test_admin_users.py 等）。
    """
    fns = build_mcp_tool_fns(None)

    role_hits = fns["retrieve_role_knowledge"](profile={}, next_stage="s", tool_query="q")
    question_hits = fns["retrieve_question_bank"](profile={}, next_stage="s", tool_query="q")
    memory_hits = fns["retrieve_candidate_memory"](profile={}, next_stage="s", tool_query="q")

    assert isinstance(role_hits, list)
    assert isinstance(question_hits, list)
    assert isinstance(memory_hits, list)


def _ok(structured_content: dict) -> FakeCallToolResult:
    return FakeCallToolResult(structured_content=structured_content)
