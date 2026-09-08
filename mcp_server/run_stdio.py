"""MCP server stdio 入口。

仓库根目录运行：`python -m mcp_server.run_stdio`。
MCPServer.run() 默认 transport="stdio"（mcp SDK 2.x），本入口不传其他参数。
文件顶部的 sys.path 引导保证 `python mcp_server/run_stdio.py` 也可直接运行
（与 mcp_server/server.py 同一模式）。
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp_server.server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run()
