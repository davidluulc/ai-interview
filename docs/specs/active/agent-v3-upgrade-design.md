# Agent v3 升级包 设计文档（SDD 总纲）

更新时间：2026-09-09

## 0. Goal Card

> 本节是本阶段的执行契约（goal 模式）：预算、范围、停止条件先谈好，执行期不再扩 scope。

**目标一句话**：把项目从「演示级」升级到「按生产标准做的 AI 面试系统」，让简历项目经历上每句技术描述在被深挖时都成立。

**范围（做）**：

```text
S1 结构化输出降级链（json_schema → function calling → 校验重试 → 兜底）
S2 向量检索 pgvector 化（vector 列 + HNSW 索引 + SQL 内计算）
S3 检索融合实验（weighted vs RRF，用现有评测 harness 出 hit@3/MRR 数字）
S4 LangGraph 真图化（条件边路由循环 + 原生 Function Calling 工具选择 + 规则 guardrail）
S5 MCP Server 化（检索/出题/复盘工具经官方 mcp SDK 暴露，主应用作 client）
加餐（时间允许才做）：Postgres checkpointer、复盘报告 SSE 流式
```

**范围（不做，含理由）**：见 §5。

**预算**：

- 总预算 4 个有效工作晚上（约 12–14 小时）+ 1 个部署窗口。
- 单阶段限时：S1 0.5 天 / S2 0.5–1 天 / S3 0.5 天 / S4 1 天 / S5 1 天；加餐各 0.5 天。

**停止条件（执行期硬约束）**：

1. 任一阶段结束前全量 `pytest -q` 必须全绿，不绿不进下一阶段。
2. 单阶段耗时超预算 1.5 倍立即停：提交现状、记录阻塞点、跳到下一独立阶段或收尾。
3. 不允许顺手修改范围外代码；发现的 unrelated bug 记入 `docs/roadmap/current-state.md` 待办，不顺手修。
4. 每阶段至少一个独立 commit，可单独回滚；动数据库的 S2 必须先备份卷。

**红线**：

- 不引入重型新框架（不加 LangChain 主包；MCP 只用官方 `mcp` SDK）。
- 不改既有数据库列含义；迁移只加不改。
- 旧 runtime（classic / langgraph_mainline）保留可回滚，新能力走灰度开关。
- 简历措辞遵循已有包装边界：动作词不加头衔词，数字必须能答口径。

## 1. 阶段定位

项目 6 月完成第一版公网部署后进入展示收口阶段。本次升级的驱动不是加功能，而是**面试竞争力**：

- 实习经历（ShieldAssist，28 PR）在简历上承担「生产化/治理」身份；本项目的职责是**补「0→1 建造」的证据链**。
- 市场共识（2026 校招）：RAG/Agent 演示项目同质化严重，区分度来自评测数字、可观测、实现真实性。本项目已有评测 harness 与诊断后台（高于平均），但存在若干「一问就穿」的实现点。
- 考点对照（`面试准备/05-Agent面试考点地图`）：模块一/二/三/五均有个人项目侧的空洞，本升级包逐项补齐。

**简历价值（升级后可诚实新增的表述素材）**：

```text
pgvector + HNSW 索引的向量检索、条件路由 Agent 循环 + 规则 guardrail 覆盖、
结构化输出三段降级链、RRF/加权融合对比评测（hit@3/MRR 数字）、MCP Server。
```

## 2. 当前问题（升级动机，均为代码事实）

1. **LangGraph 是固定直线**：`langgraph_agent/graph.py` 七节点固定顺序，无条件边无循环；「Agent 决策」不改变图走向。工具（`agent_tools.py`）固定并行全调，查询词硬编码拼接，模型无选择权。
2. **无原生工具调用 / 无 MCP**：决策 = 单次 LLM JSON 调用（`interview_agent.py:432`）+ 手写规则 fallback（`agent_policy.py` 计数规则）。
3. **向量检索是暴力扫描**：`vector_store.py:58` embedding 存 JSON 列，检索全量拉回 Python 逐条算余弦；无索引。
4. **结构化输出薄弱**：`llm_client.py` 仅 `json_object` + 手工剥代码围栏；解析失败直接 502，无降级链；传输错误与格式错误混在同一 except。
5. **评测基建闲置**：`rag_evaluation.py`（hit@k/MRR）与 seed 集已接 Celery，但从未用于做工程决策（融合权重 0.6/0.4 未验证过）。

## 3. 总体设计

### 3.1 阶段依赖与顺序

```text
S1 结构化输出 ──► S4 真图化（plan 节点依赖结构化输出）
S2 pgvector  ─┐
S3 融合实验  ─┴─►（S2 先行，S3 在 pgvector 上跑数字更可信；两者独立可并行）
S4 真图化 ──► S5 MCP（v3 runtime 的工具经 MCP 暴露）
```

执行顺序：S1 → S2 → S3 → S4 → S5。前三项互相独立、风险低；S4/S5 依赖 S1。

### 3.2 灰度与回滚（复用既有机制）

- 新 LLM 通道走 config 开关（`LLM_STRUCTURED_OUTPUT=chain|legacy`），legacy 路径原样保留。
- 新 Agent runtime 注册为 `langgraph_agent_v3`，进 `agent_runtime.py` 既有 runtime 集合，复用 quality gate / shadow 对照 / fallback classic。
- 每阶段独立 commit + 分支 `feat/agent-v3-upgrade`。

## 4. 各阶段设计

### S1 结构化输出降级链

**现状**：`call_model` 单通道；`safe_call_question_model`（`routes/interview.py:473`）出题、报告生成（`:1060`）、`decide_next_action`、`resume_parser` 全走它。

**目标设计**：新模块 `backend_python/structured_output.py`：

- 三段链：① `response_format: json_schema`（strict）→ ② function calling 强制模式（`tool_choice` required，从 `arguments` 取结构化输出）→ ③ 自由 JSON + Pydantic 校验失败定向重试一次 → 兜底值。
- 异常分层：`TransportError`（超时/429/5xx → 同段重试）vs `FormatError`（解析/校验失败 → 降级下一段）。
- 返回 `(validated_model, chain_meta)`；chain_meta 记录每段尝试结果，接入既有 ai trace。
- 本阶段接入两个调用点：Agent 决策（schema 已知）、出题（`QuestionDraftModel`）；报告/简历解析留在 legacy，后续机械迁移。

**验收**：降级链每段有单测（含 characterization：围栏 JSON 走 ③、传输错误同段重试）；两调用点结构化后行为不回退（既有测试全绿 + 新增对比断言）；legacy 开关可一键回滚。

### S2 向量检索 pgvector 化

**目标设计**：

- `docker-compose.yml` 镜像 `postgres:16` → `pgvector/pgvector:pg16`；迁移执行 `CREATE EXTENSION vector`。
- Alembic 迁移：`RagChunkEmbeddings` 加 `embedding vector(d)` 列（d 以生产 embedding-3 实际维度为准，迁移前在 config 实测确认）；JSON 列保留做回滚与对照。
- 摄取路径双写；存量数据一次性回填脚本（scripts/）。
- 查询：`ORDER BY embedding <=> :q LIMIT k` + HNSW 索引（`vector_cosine_ops`）；租户/metadata 过滤仍走 WHERE。
- 旧 Python 扫描实现保留为 fallback/对照，加新旧 top-k 一致性测试（容忍顺序差异）。

**验收**：检索结果一致性测试通过；公网数据回填完成；文档记录「HNSW + 过滤条件退化」的已知限制（面试话术素材）。

### S3 检索融合实验

**目标设计**：`retrieval_service.py` 增加 `rrf_fuse(bm25_hits, vector_hits, k=60)`；用现有 seed 评测集跑四组（纯 BM25 / 纯向量 / weighted / RRF）出 hit@3 与 MRR 表；结论写半页实验报告进 docs（含 seed 集规模局限声明）；胜者设默认、败者留可配置。

**验收**：数字落盘、报告进 docs、默认策略切换有测试佐证。

### S4 LangGraph 真图化 + 原生工具调用

**目标设计**：

- 图形状：`observe → analyze → plan ⇄ tools（ReAct 循环，N 步上限）→ generate_question → update_memory → END`；`add_conditional_edges` 路由；步数上限 = state 既有 `remainingRounds` + LangGraph `recursion_limit` 双保险。
- `plan` 节点原生 Function Calling：三检索工具注册为带 Schema 的 tools（参数 query/limit/stage），模型自主选择。
- `agent_policy` 手写规则降级为 **guardrail**：触发阈值时覆盖模型建议并记录 `overrideReason` 进 trace（复现实习「模型建议、规则执行」分层）。
- 注册 runtime `langgraph_agent_v3`，shadow 对照后切 mainline；工具选择与 override 进 nodeTrace，后台诊断工作台可见。
- 注意：`langgraph==0.2.76` 为 pinned 旧版，执行期先验证条件边/ToolNode 兼容性；不升级大版本（锁版本红线），必要时就地实现路由。

**验收**：v3 runtime 通过 quality gate 并完成 shadow 对照；追问/换方向/结束三路径集成测试；循环上限防死循环测试；override 规则测试。

### S5 MCP Server 化

**目标设计**：

- 新服务 `mcp_server/`：官方 `mcp` Python SDK；**Tools**=三检索+出题+复盘；**Resources**=知识库文档列表；**Prompts**=面试官 persona 模板（凑齐三类能力，对应考点地图模块五）。
- 主应用作 MCP client（`langchain-mcp-adapters` 或原生 client）在 v3 runtime 调用；docker-compose 增加该服务；stdio（本地）/streamable-http（容器）。
- 信任边界：MCP 返回内容进 prompt 前清洗 + 长度限制；MCP 故障 fallback 进程内直调，不阻塞主链路。
- 调用 trace 复用 `build_tool_call_summary` 进诊断后台。

**验收**：容器编排跑通；MCP 挂掉 fallback 测试；三类能力各有一个可演示用例。

## 5. 明确不做（含理由，面试可引用）

| 不做 | 理由 |
|---|---|
| GraphRAG | 查询模式是局部检索（出题捞料），无跨文档多跳查询需求；入库 LLM 抽实体成本高且评测指标未必受益。话术：「评估过，评测集里没有全局类查询，所以不上。」 |
| 微调 | 无私有标注数据量、无 GPU 预算；出题质量靠 prompt+RAG+结构化输出已覆盖。概念题照常准备。 |
| A2A | 单 Agent 系统无 Agent 间协作场景。MCP（模型↔工具）与 A2A（Agent↔Agent）分工概念必须会答。 |
| 多 Agent 框架 / GraphRAG 变体 / 域名 HTTPS | 对「AI 应用开发岗面试深挖」边际收益接近零，挤占 9 月投递窗口。 |
| LangChain 主包引入 | 现有自建 harness 与诊断是差异化卖点；标准件只取官方协议 SDK。 |

## 6. 抄作业边界（成熟方案 vs 手写）

- **用标准件**：pgvector 本体、官方 `mcp` SDK、`langgraph-checkpoint-postgres`（加餐）、`sse-starlette`（加餐）。Instructor 的「校验失败喂回重试」模式借鉴进 S1，但不引依赖（自建 200 行内）。
- **手写（卖点）**：条件路由与 guardrail（S4）、RRF 对比实验与评测报告（S3）、降级链本身（S1 的机制代码）、诊断 trace。
- 面试口径：库做的大方承认，并答「为什么选它 + 内部原理 + 什么场景不用」。

## 7. 风险与回滚

| 风险 | 缓解 |
|---|---|
| DashScope 对 json_schema strict 支持不稳 | S1 三段链天然兜底：段①失败落段② function calling（Qwen 成熟路径），机制无浪费 |
| langgraph 0.2.76 API 与新图模式差异 | S4 首个任务即 spike 验证；不升级依赖版本 |
| pgvector HNSW + 强过滤退化扫描 | 数据量级小影响有限；如实记录限制文档，作为面试话术 |
| S2 数据迁移损坏 | 动库前备份 postgres 卷；JSON 列保留双写期 |
| 评估 seed 集太小结论不稳 | S3 报告明确标注局限；结论用于「做过对比」而非「绝对最优」 |
