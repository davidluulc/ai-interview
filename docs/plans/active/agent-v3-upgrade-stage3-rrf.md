# Agent v3 Stage 3：检索融合对比实验（weighted vs RRF）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加 RRF 融合实现，用现有评测 harness（hit@k / MRR）跑四组对比（纯 BM25 / 纯向量 / hybrid-weighted / hybrid-RRF），产出数字与半页实验报告；胜者设默认、败者留可配置。

**Architecture:** `retrieval_service.py` 增加 `rrf_fuse()`（与 `merge_hybrid_hits` 同签名的姐妹函数）；`retrieve_hybrid_chunks` 增加 `fusion` 参数（`weighted | rrf`，默认经 config `HYBRID_FUSION_MODE`）；实验用脚本 `scripts/rag_fusion_experiment.py` 在本地库（seed 评测集灌入）上跑四组并输出表格；报告落 `docs/experiments/rag-fusion-comparison.md`。

**Tech Stack:** 纯既有栈，零新依赖。评测函数直接复用 `rag_evaluation.py`（`evaluate_case` / `summarize_mode_results`）与 `rag_evaluation_seed.py`（`seed_evaluation_documents` + 评测用例集）。

**上游 spec:** `docs/specs/active/agent-v3-upgrade-design.md` §4-S3、§0 Goal Card。

## Global Constraints

- 不改 `merge_hybrid_hits` / `normalize_hybrid_weights` 既有行为（weighted 是对照组）。
- 不改既有测试；新测试进 `tests/test_rag_fusion.py`。
- 数字必须来自真实运行，报告如实标注 seed 集规模局限；不允许拍脑袋填数。
- 分支 `feat/agent-v3-s3-rrf`；测试命令同前；不 push。

## 预先完成的事实（已验证）

- 融合函数：`merge_hybrid_hits(bm25_hits, vector_hits, *, limit, bm25_weight=0.6, vector_weight=0.4)`（retrieval_service.py:133）；召回侧 `retrieve_hybrid_chunks` 用 `recall_limit = max(limit*2, 6)`。
- 评测：`evaluate_case(case, hits, k)` 出 hitAtK/reciprocalRank/keywordCoverage/metadataMatch；`summarize_mode_results` 聚合 hitAtK/mrr。
- Seed：`rag_evaluation_seed.py` 有 `EVALUATION_SEED_DOCUMENTS` 与 `seed_evaluation_documents(db, user_id=1)`；评测用例集在同一文件（执行 Task 2 时确认用例列表变量名与 case 结构，`normalize_evaluation_case` 的字段为 query/knowledgeBase/expectedTitle/expectedKeywords/…）。
- Celery 评测任务是脚手架，本阶段不碰它（实验走脚本 + 服务函数）。

## File Map

- Modify: `backend_python/retrieval_service.py` — rrf_fuse + fusion 参数 + config 默认
- Modify: `backend_python/config.py` — `HYBRID_FUSION_MODE`（默认 "weighted"，实验出数后按结论切）
- Create: `tests/test_rag_fusion.py`
- Create: `scripts/rag_fusion_experiment.py`
- Create: `docs/experiments/rag-fusion-comparison.md`
- Modify: `docs/roadmap/current-state.md`

---

### Task 1: rrf_fuse（TDD 纯函数）

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Create: `tests/test_rag_fusion.py`

**Interfaces:**
- Produces:

```python
def rrf_fuse(
    bm25_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    *,
    limit: int,
    k: int = 60,
) -> list[dict[str, Any]]
```

行为契约：对两路各按名次贡献 `1/(k+rank)`（rank 从 1 起），按 chunkId 合并累加得 rrfScore，降序取 limit；输出条目含 `retrievalMode: "hybrid"`、`fusion: "rrf"`、`rrfScore`、`matchedRetrievalModes`（与 merge_hybrid_hits 的输出字段风格对齐，保留原始字段便于下游消费）。

- [ ] **Step 1: 失败测试**（4 个）：两路同 chunk 合并得分 = 1/(k+1)+1/(k+1) 且排第一；仅一路命中的 chunk 得 1/(k+1)；limit 截断；k 参数生效（k=1 时得分变化）。测试用手写 hits 字面量（含 chunkId/score/title），不 mock。
- [ ] **Step 2: 红 → 实现（约 30 行）→ 绿**
- [ ] **Step 3: commit** `feat: add rrf fusion for hybrid retrieval`

### Task 2: fusion 参数接线 + 配置默认

**Files:**
- Modify: `backend_python/retrieval_service.py`（retrieve_hybrid_chunks 加 `fusion: str = ""` 形参，空则读 `config.HYBRID_FUSION_MODE`；weighted 走 merge_hybrid_hits 原路，rrf 走 rrf_fuse）
- Modify: `backend_python/config.py`（`HYBRID_FUSION_MODE = os.getenv("HYBRID_FUSION_MODE", "weighted").strip().lower()`）
- Modify: `tests/test_rag_fusion.py`（追加 2 个测试：fusion="rrf" 时走 rrf_fuse 输出带 fusion 标记；非法值回退 weighted）

注意：`retrieve_hybrid_chunks` 的既有调用方不传 fusion → 行为不变（默认 weighted）。grep 调用方确认无隐式依赖。

- [ ] **红灯 → 实现 → 绿灯 → 全量回归 → commit** `feat: make hybrid fusion mode configurable`

### Task 3: 实验脚本 + 跑数

**Files:**
- Create: `scripts/rag_fusion_experiment.py`

**Interfaces:**
- Consumes: `seed_evaluation_documents`、`rag_evaluation_seed` 的评测用例集、`retrieve_chunks(mode=...)`、`retrieve_hybrid_chunks`、`evaluate_case` / `summarize_mode_results`。

脚本流程（同步函数即可，检索入口是同步的）：

```text
1. 连本地库（database.py SessionLocal；本地无数据则先 seed_evaluation_documents）
2. 对每个评测用例 × 四种模式取 hits：bm25 / vector / hybrid-weighted / hybrid-rrf（k=3，与现有评测口径一致）
3. 逐 case evaluate_case，按模式 summarize_mode_results
4. 输出 Markdown 表（模式 | caseCount | hit@3 | MRR | keywordCoverage）+ 每模式耗时
5. 结论段模板：胜者、差距、局限（case 数、seed 数据为人工构造、无生产流量分布）
```

- [ ] **Step 1: 写脚本 → 本地跑通**（若本地库为 SQLite 且无向量数据，vector/hybrid 两组会空召回——脚本需检测：无 ready embedding 时先打印警告并继续，报告如实记录"向量组在本地 SQLite 数据上不可评，结论仅基于 bm25/加权组的差分 + 待公网 pgvector 环境复跑"；这正是 S2 先行的意义，两阶段合并后部署窗口统一复跑）
- [ ] **Step 2: commit** `feat: add rag fusion experiment script`

### Task 4: 实验报告 + 默认值决策 + 收尾

**Files:**
- Create: `docs/experiments/rag-fusion-comparison.md`（表格数字来自 Task 3 实际输出，附运行环境与复现命令）
- Modify: `docs/roadmap/current-state.md`（S3 记录：数字、决策、复跑条件）
- 决策规则（总控执行）：若 rrf 在 hit@3 或 MRR 上 ≥ weighted，则 `HYBRID_FUSION_MODE` 默认切 "rrf"（同步改 config 默认值 + .env.example 注释 + 测试默认值断言）；否则保持 weighted，报告说明。

- [ ] 全量测试 + commit `docs: record rag fusion experiment results`
- [ ] 合并门同流水线总控。

## Self-Review（写作时已执行）

- Spec §4-S3 验收（数字落盘 / 报告 / 默认切换有测试佐证）→ Task 3/4 覆盖。
- 风险预案：本地 SQLite 无向量数据时脚本不崩溃、结论标注局限（已写入 Task 3 Step 1）。
- 红线核对：merge_hybrid_hits 零改动 ✅；既有测试零改动 ✅；零新依赖 ✅。
