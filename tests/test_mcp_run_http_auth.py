"""run_http 的 x-mcp-token 共享密钥门禁（纯 ASGI 包装层）。

MCP_AUTH_TOKEN 设置时：http 请求必须携带同值 x-mcp-token 头，否则 401；
lifespan 等非 http scope 与"未设密钥"场景原样放行。
"""

import asyncio
from typing import Any

from mcp_server.run_http import token_gate


class _Sentinel:
    """记录被包装 app 是否被调用的探针 app。"""

    def __init__(self) -> None:
        self.called_scopes: list[str] = []

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        self.called_scopes.append(str(scope.get("type")))


def _run(wrapped: Any, scope: dict) -> tuple[int, list[bytes]]:
    status: dict = {}
    body: list[bytes] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            status["code"] = int(message["status"])
        elif message["type"] == "http.response.body":
            body.append(bytes(message.get("body") or b""))

    asyncio.run(wrapped(scope, receive, send))
    return status.get("code", 0), body


def _http_scope(token: str | None) -> dict:
    headers = [(b"content-type", b"application/json")]
    if token is not None:
        headers.append((b"x-mcp-token", token.encode()))
    return {"type": "http", "headers": headers, "path": "/mcp", "method": "POST"}


def test_matching_token_passes_through_to_app() -> None:
    sentinel = _Sentinel()
    wrapped = token_gate(sentinel, "s3cret")
    code, _ = _run(wrapped, _http_scope("s3cret"))
    assert code == 0  # 探针 app 不回响应，未拦截即通过
    assert sentinel.called_scopes == ["http"]


def test_missing_or_wrong_token_gets_401_without_touching_app() -> None:
    sentinel = _Sentinel()
    wrapped = token_gate(sentinel, "s3cret")

    code, body = _run(wrapped, _http_scope(None))
    assert code == 401
    assert b"unauthorized" in b"".join(body)

    code, _ = _run(wrapped, _http_scope("wrong"))
    assert code == 401
    assert sentinel.called_scopes == []  # 门禁拦截，app 从未被调用


def test_non_http_scopes_pass_through() -> None:
    sentinel = _Sentinel()
    wrapped = token_gate(sentinel, "s3cret")
    code, _ = _run(wrapped, {"type": "lifespan", "headers": []})
    assert code == 0
    assert sentinel.called_scopes == ["lifespan"]
