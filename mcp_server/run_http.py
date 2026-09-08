"""MCP server streamable-http 入口。

仓库根目录运行：`python -m mcp_server.run_http`。
绑定地址由环境变量驱动（默认 127.0.0.1:8000），路径固定 /mcp：
- MCP_HOST（默认 127.0.0.1，未认证 transport 不默认绑全网卡；容器/compose 场景显式设 MCP_HOST=0.0.0.0 覆盖）
- MCP_PORT（默认 8000，设置为空时回退默认值而非崩溃）

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

# 默认只绑回环（transport 无认证）；compose/容器需要对外时显式设 MCP_HOST=0.0.0.0 覆盖。
# 空值一律回退安全默认（host="" 会被服务端当全网卡绑定，不能放行）。
MCP_HOST = os.getenv("MCP_HOST") or "127.0.0.1"
MCP_PORT = int(os.getenv("MCP_PORT") or "8000")
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
