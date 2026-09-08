# Agent v3 Stage 5：MCP Server 化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用官方 mcp SDK v2 把三个检索工具 + 出题 + 复盘暴露为独立 MCP Server（Tools / Resources / Prompts 三类能力齐备）；后端 v3 runtime 经 `MCP_TOOLS_ENABLED` 开关优先走 MCP 客户端调用、故障回落进程内直调；docker-compose 增加 mcp 服务。

**Architecture:** 新目录 `mcp_server/`：`server.py`（MCPServer 实例 + @m.tool 装饰器包装既有服务函数）、`run_stdio.py` / `run_http.py` 两个入口。后端新增 `backend_python/mcp_tools_client.py`：streamable-http 客户端 + 与 `agent_tools.py` 同签名的包装（供 graph_v3 的 tool_fns 注入），带超时、返回内容清洗（长度上限 + 去控制字符，信任边界）与进程内 fallback。依赖：`mcp>=2.2,<3`（**唯一允许的新增依赖**，spec §6 授权的官方 SDK；已验证 v2 API：`from mcp.server.mcpserver import MCPServer`、`@m.tool()`、`await m.list_tools()`）。

**上游 spec:** `docs/specs/active/agent-v3-upgrade-design.md` §4-S5（spec 中 FastMCP 字样已按 v2 更新为 MCPServer）。

## Global Constraints

- 新依赖仅 `mcp>=2.2,<3`（requirements.txt 一行）；其余零新增。
- 不改既有服务函数行为（MCP 只是包装层）；不改既有测试。
- MCP 通道默认关闭：`MCP_TOOLS_ENABLED` 默认 `false`，`MCP_SERVER_URL` 默认 `http://mcp:8000/mcp`。
- 信任边界：客户端对 MCP 返回做 `sanitize_mcp_content()`（strip 控制字符 + 截断 4000 字符/条），防注入进 prompt。
- 分支 `feat/agent-v3-s5-mcp`；不 push。

## File Map

- Create: `mcp_server/__init__.py`、`mcp_server/server.py`、`mcp_server/run_stdio.py`、`mcp_server/run_http.py`
- Create: `backend_python/mcp_tools_client.py`
- Create: `tests/test_mcp_server.py`、`tests/test_mcp_tools_client.py`
- Modify: `requirements.txt`、`docker-compose.yml`（mcp 服务 + app 依赖）、`.env.example`/`.env.production.example`
- Modify: `docs/roadmap/current-state.md`

---

### Task 1: 依赖安装 + server 骨架（Tools）

**Files:**
- Modify: `requirements.txt`（`mcp>=2.2,<3`）
- Create: `mcp_server/server.py` 等

- [ ] **Step 1:** `uv pip install -p .venv/bin/python "mcp>=2.2,<3"`；requirements.txt 追加一行。
- [ ] **Step 2:** `mcp_server/server.py`——每个工具是既有同步服务函数的薄包装（进程内自建 SessionLocal）：

```python
from mcp.server.mcpserver import MCPServer

from backend_python.database import SessionLocal
from backend_python.retrieval_service import retrieve_chunks

mcp = MCPServer("ai-interview-rag")


@mcp.tool()
def retrieve_role_knowledge(query: str, limit: int = 3) -> list[dict]:
    """按查询词检索岗位知识库（BM25）。返回 title/content/score/metadata。"""
    db = SessionLocal()
    try:
        return retrieve_chunks(db, user_id=1, knowledge_base="role_knowledge", query=query, limit=limit, mode="bm25")
    finally:
        db.close()
```

（user_id 固定 1 的服务账号模式先落骨架——多租户经 MCP 上下文传递标记为已知限制写入 server docstring 与 current-state 待办；另两个检索工具同型。出题/复盘两个工具签名：`draft_interview_question(profile_json: str, stage: str) -> dict`、`generate_report(plan_json: str, answers_json: str) -> dict`，内部各包一层 json.loads + 既有服务函数。）

- [ ] **Step 3: 冒烟**（既是验证也是测试）：

```bash
.venv/bin/python -c "
import anyio
from mcp_server.server import mcp
async def smoke():
    tools = await mcp.list_tools()
    print([t.name for t in tools])
anyio.run(smoke)"
```

Expected: 5 个工具名。→ commit `feat: add mcp server with five tools`

### Task 2: Resources + Prompts + stdio/http 入口

- [ ] `@mcp.resource("rag://knowledge-bases")`（返回三库说明 JSON）与 `@mcp.prompt()` 两个（面试官 persona / coach persona 模板，从 `backend_python/prompts` 既有文案取材）；`run_stdio.py` = `mcp.run()`；`run_http.py` = streamable-http transport（按 v2 SDK 的 `mcp.settings`/run(transport=...) 惯例，装包后以 `inspect.signature` 核对一次再落码——**本步骤含 5 分钟 API 核对**）。
- [ ] 测试（tests/test_mcp_server.py，本地无需起服务）：`list_tools` 5 项、`list_resources`/`list_prompts` 各 ≥1 项、`call_tool("retrieve_role_knowledge", {"query": "RAG", "limit": 2})` 返回 list（走 SQLite 本地库；库空则空列表，断言类型不断言内容）。
- [ ] commit `feat: add mcp resources prompts and transports`

### Task 3: 客户端适配层（TDD，可 fake）

**Files:**
- Create: `backend_python/mcp_tools_client.py`
- Create: `tests/test_mcp_tools_client.py`

**Interfaces:**
- Produces:

```python
def sanitize_mcp_content(text: str, *, max_chars: int = 4000) -> str   # 纯函数
def build_mcp_tool_fns(client_factory) -> dict[str, Callable]         # 与 agent_tools 的 tool_fns 同构，供 graph_v3 注入
async def call_tool_with_fallback(tool: str, payload: dict, *, in_process_fn) -> dict  # MCP 失败/超时/开关关 → in_process_fn
```

- [ ] **Step 1: 失败测试**（4 个）：sanitize 截断与去控制字符；fake client 返回 → 工具 fn 返回结构含 result/toolCall 摘要；fake client 抛超时 → fallback 到 in_process_fn 且 toolCall 标 `transport: "mcp-fallback"`；开关关闭 → 直接 in_process。
- [ ] **Step 2: 实现**（官方客户端：`from mcp import ClientSession` + streamablehttp_client，超时 5s）→ 绿灯 → commit `feat: add mcp tools client with sanitize and fallback`

### Task 4: compose 服务 + 环境变量 + 集成冒烟

- [ ] docker-compose.yml 增加 `mcp` 服务（同 app 镜像，command 跑 `python -m mcp_server.run_http`，expose 8000，depends_on db）；app 服务加 `MCP_SERVER_URL`/`MCP_TOOLS_ENABLED` 环境变量；`docker compose --env-file .env.production.example config --quiet` exit 0。
- [ ] 本地集成冒烟（测试内标记，默认 skip）：起 `run_http` 子进程 → 客户端 call_tool 往返一次成功（门控 `MCP_INTEGRATION=1`）。
- [ ] commit `feat: add mcp compose service and env wiring`

### Task 5: 阶段收尾

- [ ] 全量回归 + `current-state.md` 记录（三类能力清单、信任边界实现、已知限制：服务账号 user_id=1、多租户后续经 context 传递；公网部署窗口再启用开关）。
- [ ] commit `docs: record stage5 mcp completion`；合并门按流水线总控。

## Self-Review（写作时已执行）

- Spec §4-S5 验收（编排跑通 / fallback 测试 / 三类能力可演示）→ Task 4 / Task 3 / Task 2 对应。
- 执行时核对点两处：v2 http transport 的 run 参数（Task 2 内置 5 分钟核对）、compose command 路径——均小且有验证步骤兜底。
- 红线核对：唯一新依赖 = mcp 官方 SDK ✅；既有服务函数零改动 ✅；默认关闭 ✅。
