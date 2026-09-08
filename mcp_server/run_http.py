"""MCP server streamable-http 入口。

仓库根目录运行：`python -m mcp_server.run_http`。
绑定地址由环境变量驱动（默认 0.0.0.0:8000），路径固定 /mcp：
- MCP_HOST（默认 0.0.0.0）
- MCP_PORT（默认 8000）

v2 API 说明（以 inspect.signature 核对，mcp SDK 2.2.0）：host/port/path 是
run_streamable_http_async 的关键字参数，经 mcp.run("streamable-http", **kwargs)
透传；MCPServer.__init__ 不接受 host/port（与 v1 FastMCP 的 settings 模式不同）。
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_server.server import mcp  # noqa: E402

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
STREAMABLE_HTTP_PATH = "/mcp"


def main() -> None:
    mcp.run(
        "streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        streamable_http_path=STREAMABLE_HTTP_PATH,
    )


if __name__ == "__main__":
    main()
