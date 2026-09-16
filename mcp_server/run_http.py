"""MCP server streamable-http 入口。

仓库根目录运行：`python -m mcp_server.run_http`。
绑定地址由环境变量驱动（默认 127.0.0.1:8000），路径固定 /mcp：
- MCP_HOST（默认 127.0.0.1；容器/compose 场景显式设 MCP_HOST=0.0.0.0 覆盖）
- MCP_PORT（默认 8000，设置为空时回退默认值而非崩溃）
- MCP_AUTH_TOKEN（设置时校验 x-mcp-token 共享密钥，不匹配返回 401；
  不设 = 本地开发不校验。生产建议设置，配合 compose 内网构成双重边界）

鉴权实现：不用 mcp.run() 的内置 uvicorn，改为取 mcp.streamable_http_app()
（标准 Starlette 应用）套一层纯 ASGI 头部校验再交给 uvicorn。lifespan 等
非 http scope 原样透传，语义与 SDK 自带 runner 等价（其内部同样是
uvicorn.Config(starlette_app) 直跑）。
"""

import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_server.server import mcp  # noqa: E402

# 默认只绑回环；compose/容器需要对外时显式设 MCP_HOST=0.0.0.0 覆盖。
# 空值一律回退安全默认（host="" 会被服务端当全网卡绑定，不能放行）。
MCP_HOST = os.getenv("MCP_HOST") or "127.0.0.1"
MCP_PORT = int(os.getenv("MCP_PORT") or "8000")
STREAMABLE_HTTP_PATH = "/mcp"
MCP_AUTH_TOKEN = (os.getenv("MCP_AUTH_TOKEN") or "").strip()


def token_gate(app: Any, expected_token: str) -> Any:
    """纯 ASGI 包装：http 请求未携带匹配的 x-mcp-token 时直接回 401。"""

    async def _unauthorized(send: Any) -> None:
        body = b'{"error":"unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def wrapped(scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers") or []
            }
            if headers.get("x-mcp-token") != expected_token:
                await _unauthorized(send)
                return
        await app(scope, receive, send)

    return wrapped


def main() -> None:
    import uvicorn

    starlette_app = mcp.streamable_http_app(
        streamable_http_path=STREAMABLE_HTTP_PATH,
        host=MCP_HOST,
    )
    app = token_gate(starlette_app, MCP_AUTH_TOKEN) if MCP_AUTH_TOKEN else starlette_app
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
