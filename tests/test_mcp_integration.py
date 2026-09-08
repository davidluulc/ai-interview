"""门控 MCP 集成冒烟（默认 skip，不进常规 CI 循环）。

运行方式：``MCP_INTEGRATION=1 .venv/bin/python -m pytest tests/test_mcp_integration.py -q``

流程：子进程起 ``python -m mcp_server.run_http``（MCP_HOST=127.0.0.1、
MCP_PORT=8231，避开常用端口）→ 等端口就绪 → 用真实
``build_streamable_http_factory`` 经 ``call_tool_with_fallback`` 调用
retrieve_role_knowledge 一次 → 断言 transport=="mcp" 且结果为 list。
服务端进程会对本地 dev sqlite 做只读检索（retrieve 语义只 SELECT），
空库返回 [] 也算通过。子进程在 finally 中终止。
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

pytestmark = pytest.mark.skipif(
    os.getenv("MCP_INTEGRATION") != "1",
    reason="MCP 集成冒烟默认跳过：需 MCP_INTEGRATION=1 显式开启",
)

from backend_python.mcp_tools_client import (  # noqa: E402
    build_streamable_http_factory,
    call_tool_with_fallback,
)

MCP_SMOKE_PORT = 8231


def _wait_for_port(port: int, *, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise TimeoutError(f"mcp server did not listen on 127.0.0.1:{port}")


def test_streamable_http_roundtrip_via_call_tool_with_fallback() -> None:
    env = {**os.environ, "MCP_HOST": "127.0.0.1", "MCP_PORT": str(MCP_SMOKE_PORT)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.run_http"],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(MCP_SMOKE_PORT)
        factory = build_streamable_http_factory(f"http://127.0.0.1:{MCP_SMOKE_PORT}/mcp")

        async def _roundtrip() -> dict:
            return await call_tool_with_fallback(
                "retrieve_role_knowledge",
                {"query": "RAG", "limit": 2},
                in_process_fn=lambda: [{"fallback": True}],
                client_factory=factory,
            )

        outcome = asyncio.run(_roundtrip())
        assert outcome["transport"] == "mcp", f"expected mcp transport, got: {outcome}"
        # 只读检索：DB 命中或空库 [] 都合法，只断言形状（sanitize 不破坏 list 结构）
        assert isinstance(outcome["result"], list)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
