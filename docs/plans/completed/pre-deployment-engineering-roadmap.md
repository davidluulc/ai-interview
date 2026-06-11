# Pre-Deployment Engineering Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the pre-deployment engineering roadmap for the AI mock interview system through a verifiable baseline, RAG engineering V2, and optional Agent V3 preparation without starting real cloud deployment.

**Architecture:** Keep the existing FastAPI + plain HTML/CSS/JS architecture. Build on the existing RAG modules (`rag_evaluation.py`, `rag_evaluation_seed.py`, `rag_explain.py`, `rag_quality.py`, `retrieval_service.py`) instead of replacing them. Treat each phase as an independently verifiable increment with tests, Chinese learning docs, and progress records.

**Tech Stack:** Python, FastAPI, pytest, JSON seed files, plain JavaScript `.mjs` tests, HTML/CSS, in-app browser verification.

## Current Execution Status

This plan was used as the original implementation checklist. The authoritative phase-by-phase execution record is now maintained in:

```text
docs/pre-deployment-progress.md
```

Current status:

- Stage 0: completed.
- Stage 1A / 1B / 1C: completed.
- Stage 2A: completed as a staged Agent V3 increment.
- Stage 3: completed as a staged training-loop increment, including weak tags, candidate memory aggregation, and frontend one-click weak-topic retry.
- Stage 4: completed as documentation-only pre-deployment preparation.

The unchecked boxes below are preserved as the original task recipe; do not treat them as the latest completion source.

---

## File Structure

- Create: `docs/learning/00-项目当前架构与进度复盘.md`
  - Stage 0 learning document: current architecture, test baseline, module map, progress state.
- Create: `docs/learning/01-RAG知识库样例与评估数据集.md`
  - Stage 1A learning document: why seed data and evaluation cases exist, how to explain them in interviews.
- Create: `docs/learning/02-RAG质量评估指标HitK-MRR-关键词覆盖率.md`
  - Stage 1B learning document: Hit@K, MRR, keyword coverage, metadata match, empty recall.
- Create: `docs/learning/03-RAG可观测面板怎么设计.md`
  - Stage 1C learning document: how RAG quality and hit explanations are exposed to users/developers.
- Create or modify: `docs/pre-deployment-progress.md`
  - Running progress record for phases completed, verification commands, risks, next steps.
- Create: `tests/test_pre_deployment_rag_v2.py`
  - Tests for the new pre-deployment RAG batch and case completeness.
- Modify: `data/role_knowledge_seed.json`
  - Add a small pre-deployment RAG batch using existing schema.
- Modify: `data/question_bank_seed.json`
  - Add matching interview questions using existing schema.
- Modify: `data/rag_evaluation_cases.json`
  - Add matching evaluation cases.
- Modify: `backend_python/rag_evaluation_seed.py`
  - Add matching evaluation seed documents for retrieval evaluation.
- Modify: `backend_python/rag_evaluation.py`
  - Add evaluation explanation helpers if missing.
- Create or modify: `tests/test_rag_evaluation_explanations.py`
  - Tests for metric explanations and case-level learning summary.
- Modify: `backend_python/rag_explain.py`
  - Add keyword coverage and quality explanation summaries for debug output if missing.
- Modify: `backend_python/routes/rag.py`
  - Include RAG explanations in `/api/rag/debug` without breaking existing fields.
- Modify: `tests/test_rag_debug_quality.py`
  - Verify debug API returns explanation summaries.
- Modify: `tests/frontend_rag_quality.test.mjs`
  - Verify frontend renders RAG explanation fields.
- Modify: `app.js`
  - Render new RAG quality/explanation summary in the existing debug panel.
- Modify: `styles.css`
  - Add compact styles for RAG explanation summaries.
- Optional create: `docs/superpowers/specs/2026-06-10-agent-engineering-v3-design.md`
  - Agent V3 design if time allows after RAG V2.

Because the worktree already contains many pre-existing untracked and modified files, this plan does not include automatic git commit steps. Do not commit unless the user explicitly asks.

---

## Stage 0: Project Baseline And Progress Record

### Task 0.1: Run Baseline Verification

**Files:**
- Create: `docs/learning/00-项目当前架构与进度复盘.md`
- Create or modify: `docs/pre-deployment-progress.md`

- [ ] **Step 1: Run backend baseline**

Run:

```powershell
python -m pytest -q
```

Expected: all existing backend tests pass. Record the pass count and runtime in `docs/pre-deployment-progress.md`.

- [ ] **Step 2: Run frontend baseline**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all existing frontend tests pass. Record the result in `docs/pre-deployment-progress.md`.

- [ ] **Step 3: Create Stage 0 learning document**

Create `docs/learning/00-项目当前架构与进度复盘.md` with these sections:

```markdown
# 00 项目当前架构与进度复盘

## 1. 当前项目定位

AI 模拟面试系统面向大学生、应届生和社会求职者，核心流程是：用户填写简历/JD/岗位信息，后端结合三类 RAG 和 Interview Orchestrator Agent 生成动态面试问题，面试结束后生成复盘报告和训练建议。

## 2. 当前核心模块

- 前端：`index.html`、`styles.css`、`app.js`，负责投递档案、面试训练工作台、RAG/Agent 调试面板和报告展示。
- 后端入口：`backend_python/main.py`，负责注册 FastAPI 应用、路由和中间件。
- 用户系统：`backend_python/auth.py`、`backend_python/routes/auth.py`、`backend_python/db_models.py`。
- 投递档案：`backend_python/routes/application_profiles.py`。
- 三类 RAG：岗位知识库、题库 RAG、候选人画像 RAG。
- RAG 工程化：`retrieval_service.py`、`rag_evaluation.py`、`rag_quality.py`、`rag_explain.py`、`rag_logging.py`。
- Agent 工程化：`interview_agent.py`、`agent_state.py`、`agent_tools.py`、`agent_trace.py`、`agent_logging.py`。

## 3. 当前测试基线

记录本阶段运行的后端测试、前端测试结果和时间。

## 4. 为什么先补 RAG 工程化

RAG 是 AI 应用开发岗最容易被深挖的能力之一。当前系统已经具备检索、日志和基础评估，但还需要把 seed 数据、评估 case、指标解释和前端可观测面板串成闭环。

## 5. 面试时怎么讲

我没有急着上线，而是先做上线前工程化补强。第一步是确认当前系统结构和测试基线，然后优先补强 RAG，因为 RAG 质量会直接影响面试官提问是否贴合岗位、简历和历史回答。
```

- [ ] **Step 4: Create or update progress record**

Create or update `docs/pre-deployment-progress.md` with:

```markdown
# 上线部署前综合补强进度记录

## 当前目标

根据 `docs/superpowers/specs/2026-06-10-pre-deployment-engineering-roadmap-design.md` 推进上线部署前综合补强。

## 阶段状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 阶段 0：项目体检与执行基线 | 进行中 | 记录测试基线、模块地图和风险。 |
| 阶段 1A：RAG seed 与 evaluation case | 未开始 | 补充可验证知识样例。 |
| 阶段 1B：RAG 指标与命中解释 | 未开始 | 补充指标解释和 case insight。 |
| 阶段 1C：RAG 可观测前端增强 | 未开始 | 展示 RAG 质量和命中解释。 |
| 阶段 2A：Agent V3 设计与第一步 | 未开始 | 时间允许时启动。 |

## 测试基线

- 后端：待记录。
- 前端：待记录。

## 风险记录

- 当前工作区存在大量未跟踪和已修改文件，本轮不自动 commit。
```

- [ ] **Step 5: Verify Stage 0 documents exist**

Run:

```powershell
Test-Path docs/learning/00-项目当前架构与进度复盘.md; Test-Path docs/pre-deployment-progress.md
```

Expected: both output `True`.

---

## Stage 1A: RAG Seed And Evaluation Case Batch

### Task 1.1: Write Data Quality Tests For Pre-Deployment RAG Batch

**Files:**
- Create: `tests/test_pre_deployment_rag_v2.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pre_deployment_rag_v2.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE_PATH = ROOT / "data" / "role_knowledge_seed.json"
QUESTION_PATH = ROOT / "data" / "question_bank_seed.json"
CASE_PATH = ROOT / "data" / "rag_evaluation_cases.json"

ROLE_IDS = {
    "predeploy_rag_query_rewrite",
    "predeploy_rag_chunk_metadata",
    "predeploy_rag_quality_dashboard",
    "predeploy_agent_rag_collaboration",
    "predeploy_backend_error_logging",
    "predeploy_deployment_readiness",
}

QUESTION_IDS = {
    "qb_predeploy_rag_001",
    "qb_predeploy_rag_002",
    "qb_predeploy_rag_003",
    "qb_predeploy_agent_001",
    "qb_predeploy_backend_001",
    "qb_predeploy_deploy_001",
}

CASE_IDS = {
    "eval_predeploy_rag_query_rewrite",
    "eval_predeploy_rag_chunk_metadata",
    "eval_predeploy_rag_quality_dashboard",
    "eval_predeploy_agent_rag_collaboration",
    "eval_predeploy_backend_error_logging",
    "eval_predeploy_deployment_readiness",
}


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item["id"]): item for item in items}


def test_pre_deployment_role_knowledge_entries_are_complete() -> None:
    items = by_id(load_json(ROLE_PATH))
    assert ROLE_IDS.issubset(items)

    for item_id in ROLE_IDS:
        item = items[item_id]
        assert item["role"] in {"AI 应用开发实习生", "Python 后端开发实习生"}
        assert item["category"]
        assert item["title"]
        assert isinstance(item["keywords"], list) and len(item["keywords"]) >= 6
        assert len(item["content"]) >= 100
        assert isinstance(item["follow_up_questions"], list) and len(item["follow_up_questions"]) >= 3
        assert isinstance(item["scoring_points"], list) and len(item["scoring_points"]) >= 4
        assert isinstance(item["risk_signals"], list) and len(item["risk_signals"]) >= 3


def test_pre_deployment_question_bank_entries_are_complete() -> None:
    items = by_id(load_json(QUESTION_PATH))
    assert QUESTION_IDS.issubset(items)

    for item_id in QUESTION_IDS:
        item = items[item_id]
        assert item["position_tag"] in {"ai_app_intern", "python_backend_intern"}
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert len(item["question"]) >= 20
        assert len(item["reference_answer"]) >= 60
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4


def test_pre_deployment_evaluation_cases_are_complete() -> None:
    cases = by_id(load_json(CASE_PATH))
    assert CASE_IDS.issubset(cases)

    for case_id in CASE_IDS:
        case = cases[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_pre_deployment_rag_v2.py -q
```

Expected: FAIL because the `predeploy_*` seed and evaluation records do not exist yet.

### Task 1.2: Add Seed Data And Evaluation Cases

**Files:**
- Modify: `data/role_knowledge_seed.json`
- Modify: `data/question_bank_seed.json`
- Modify: `data/rag_evaluation_cases.json`
- Modify: `backend_python/rag_evaluation_seed.py`

- [ ] **Step 1: Add role knowledge records**

Append six records to `data/role_knowledge_seed.json` using the existing schema:

| id | role | title | required keywords |
| --- | --- | --- | --- |
| `predeploy_rag_query_rewrite` | `AI 应用开发实习生` | `RAG Query Rewrite 与多路召回` | `RAG`, `query rewrite`, `多路召回`, `BM25`, `向量检索`, `metadata` |
| `predeploy_rag_chunk_metadata` | `AI 应用开发实习生` | `Chunk 切分与 Metadata 设计` | `chunk`, `metadata`, `文档切分`, `页码`, `章节`, `权限` |
| `predeploy_rag_quality_dashboard` | `AI 应用开发实习生` | `RAG 质量评估与可观测面板` | `Hit@K`, `MRR`, `关键词覆盖率`, `emptyRecall`, `metadataMatch`, `调试面板` |
| `predeploy_agent_rag_collaboration` | `AI 应用开发实习生` | `Agent 与三类 RAG 协作` | `Agent State`, `ToolCalls`, `岗位知识库`, `题库`, `候选人画像`, `决策` |
| `predeploy_backend_error_logging` | `Python 后端开发实习生` | `FastAPI 错误处理与请求日志` | `FastAPI`, `HTTPException`, `中间件`, `请求日志`, `状态码`, `trace` |
| `predeploy_deployment_readiness` | `Python 后端开发实习生` | `上线前工程化准备` | `Uvicorn`, `Nginx`, `Redis`, `环境变量`, `数据库`, `日志` |

Each record must include at least 100 Chinese characters in `content`, 3 follow-up questions, 4 scoring points, and 3 risk signals.

- [ ] **Step 2: Add question bank records**

Append six records to `data/question_bank_seed.json`:

| id | position_tag | difficulty | question |
| --- | --- | --- | --- |
| `qb_predeploy_rag_001` | `ai_app_intern` | `medium` | `如果用户问题很短，你会如何做 query rewrite 来提升 RAG 召回质量？` |
| `qb_predeploy_rag_002` | `ai_app_intern` | `medium` | `RAG chunk 的 metadata 里为什么要记录文档名、章节、权限和时间戳？` |
| `qb_predeploy_rag_003` | `ai_app_intern` | `hard` | `你如何用 Hit@K、MRR、关键词覆盖率判断一次 RAG 检索是否可靠？` |
| `qb_predeploy_agent_001` | `ai_app_intern` | `hard` | `你的 Agent 如何结合三个 RAG 的结果决定继续深挖还是切换话题？` |
| `qb_predeploy_backend_001` | `python_backend_intern` | `medium` | `FastAPI 后端如何通过错误处理和请求日志提升线上可排查性？` |
| `qb_predeploy_deploy_001` | `python_backend_intern` | `medium` | `上线前为什么要提前规划 Uvicorn、Nginx、Redis、数据库和环境变量？` |

Each record must include a `reference_answer` of at least 60 Chinese characters, at least 4 `key_points`, and at least 4 `tags`.

- [ ] **Step 3: Add evaluation cases**

Append six records to `data/rag_evaluation_cases.json`:

```json
[
  {
    "id": "eval_predeploy_rag_query_rewrite",
    "query": "RAG query rewrite 和多路召回如何提升检索质量？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "ai_app_intern",
    "expectedStage": "RAG 追问",
    "expectedTitle": "RAG Query Rewrite 与多路召回",
    "expectedKeywords": ["query rewrite", "多路召回", "BM25", "向量检索"]
  },
  {
    "id": "eval_predeploy_rag_chunk_metadata",
    "query": "RAG chunk metadata 为什么要记录章节、页码和权限？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "ai_app_intern",
    "expectedStage": "RAG 追问",
    "expectedTitle": "Chunk 切分与 Metadata 设计",
    "expectedKeywords": ["chunk", "metadata", "章节", "权限"]
  },
  {
    "id": "eval_predeploy_rag_quality_dashboard",
    "query": "如何用 Hit@K、MRR 和关键词覆盖率做 RAG 质量评估？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "ai_app_intern",
    "expectedStage": "RAG 评估",
    "expectedTitle": "RAG 质量评估与可观测面板",
    "expectedKeywords": ["Hit@K", "MRR", "关键词覆盖率", "调试面板"]
  },
  {
    "id": "eval_predeploy_agent_rag_collaboration",
    "query": "Agent 如何结合岗位知识库、题库和候选人画像做下一步决策？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "ai_app_intern",
    "expectedStage": "Agent 追问",
    "expectedTitle": "Agent 与三类 RAG 协作",
    "expectedKeywords": ["Agent State", "ToolCalls", "岗位知识库", "候选人画像"]
  },
  {
    "id": "eval_predeploy_backend_error_logging",
    "query": "FastAPI 请求日志和统一错误处理如何帮助线上排查？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "python_backend_intern",
    "expectedStage": "工程化追问",
    "expectedTitle": "FastAPI 错误处理与请求日志",
    "expectedKeywords": ["FastAPI", "HTTPException", "请求日志", "状态码"]
  },
  {
    "id": "eval_predeploy_deployment_readiness",
    "query": "上线前为什么要规划 Uvicorn、Nginx、Redis、环境变量和数据库？",
    "knowledgeBase": "role_knowledge",
    "expectedKnowledgeBase": "role_knowledge",
    "expectedPositionTag": "python_backend_intern",
    "expectedStage": "部署追问",
    "expectedTitle": "上线前工程化准备",
    "expectedKeywords": ["Uvicorn", "Nginx", "Redis", "环境变量"]
  }
]
```

- [ ] **Step 4: Add matching evaluation seed documents**

In `backend_python/rag_evaluation_seed.py`, append six records to `EVALUATION_SEED_DOCUMENTS` with matching `caseId`, `knowledgeBase`, `title`, `content`, `metadata`, and `embedding`. Use these deterministic embeddings:

| caseId | embedding |
| --- | --- |
| `eval_predeploy_rag_query_rewrite` | `[1.0, 0.4, 0.0]` |
| `eval_predeploy_rag_chunk_metadata` | `[1.0, 0.5, 0.0]` |
| `eval_predeploy_rag_quality_dashboard` | `[1.0, 0.6, 0.0]` |
| `eval_predeploy_agent_rag_collaboration` | `[0.2, 0.1, 1.0]` |
| `eval_predeploy_backend_error_logging` | `[0.0, 1.0, 0.2]` |
| `eval_predeploy_deployment_readiness` | `[0.0, 1.0, 0.4]` |

The `metadata` for each document must include `category`, `caseId`, `positionTag`, and `interviewStage`.

- [ ] **Step 5: Run data tests**

Run:

```powershell
python -m pytest tests/test_pre_deployment_rag_v2.py tests/test_rag_knowledge_curriculum_v2.py tests/test_rag_evaluation_seed.py -q
```

Expected: PASS.

- [ ] **Step 6: Create Stage 1A learning document**

Create `docs/learning/01-RAG知识库样例与评估数据集.md` with:

```markdown
# 01 RAG 知识库样例与评估数据集

## 1. 为什么 RAG 需要 seed 数据

seed 数据是项目初始知识库，能让系统在没有用户自建知识库时也有可检索资料。

## 2. 为什么 RAG 需要 evaluation case

evaluation case 用固定问题验证检索链路，避免只凭感觉判断“好像能搜到”。

## 3. 本阶段新增内容

本阶段围绕 query rewrite、chunk metadata、RAG 质量面板、Agent 与 RAG 协作、后端错误日志、上线前准备补充了可验证样例。

## 4. 面试时怎么讲

我没有把知识库做成无法维护的百科全书，而是把高频、可追问、可评估的知识点分批进入 seed。每条 seed 都对应 evaluation case，能用测试证明检索链路是否命中预期资料。
```

---

## Stage 1B: RAG Metrics And Hit Explanation

### Task 1.3: Add Evaluation Explanation Helpers

**Files:**
- Modify: `backend_python/rag_evaluation.py`
- Create: `tests/test_rag_evaluation_explanations.py`
- Create: `docs/learning/02-RAG质量评估指标HitK-MRR-关键词覆盖率.md`

- [ ] **Step 1: Write failing tests**

Create `tests/test_rag_evaluation_explanations.py`:

```python
from backend_python.rag_evaluation import build_case_insight, explain_evaluation_metrics


def test_explain_evaluation_metrics_returns_chinese_learning_text() -> None:
    explanations = explain_evaluation_metrics()

    assert "hitAtK" in explanations
    assert "MRR" in explanations["mrr"]
    assert "关键词覆盖率" in explanations["keywordCoverage"]
    assert "metadata" in explanations["metadataMatch"]
    assert "空召回" in explanations["emptyRecall"]


def test_build_case_insight_marks_successful_case() -> None:
    insight = build_case_insight(
        {
            "caseId": "case_ok",
            "query": "RAG 质量评估指标有哪些？",
            "hitAtK": 1,
            "reciprocalRank": 1.0,
            "keywordCoverage": 0.75,
            "metadataMatch": 1,
            "emptyRecall": 0,
            "topTitles": ["RAG 质量评估与可观测面板"],
        }
    )

    assert insight["level"] == "good"
    assert "命中预期资料" in insight["summary"]
    assert "RAG 质量评估与可观测面板" in insight["evidence"]


def test_build_case_insight_marks_weak_case_with_action() -> None:
    insight = build_case_insight(
        {
            "caseId": "case_weak",
            "query": "RAG metadata 权限怎么做？",
            "hitAtK": 0,
            "reciprocalRank": 0.0,
            "keywordCoverage": 0.25,
            "metadataMatch": 0,
            "emptyRecall": 0,
            "topTitles": ["无关资料"],
        }
    )

    assert insight["level"] == "weak"
    assert "未命中预期资料" in insight["summary"]
    assert "补充 seed" in insight["action"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_rag_evaluation_explanations.py -q
```

Expected: FAIL because `build_case_insight` and `explain_evaluation_metrics` do not exist.

- [ ] **Step 3: Implement helper functions**

Add to `backend_python/rag_evaluation.py`:

```python
def explain_evaluation_metrics() -> dict[str, str]:
    return {
        "hitAtK": "Hit@K 表示前 K 条召回结果里是否命中预期资料，适合判断检索有没有找对方向。",
        "mrr": "MRR 是 Mean Reciprocal Rank，关注正确资料排在第几位，越靠前分数越高。",
        "keywordCoverage": "关键词覆盖率表示召回结果覆盖了多少预期关键词，用来判断内容是否贴合问题。",
        "metadataMatch": "metadataMatch 判断命中资料的知识库、岗位标签或面试阶段是否符合预期。",
        "emptyRecall": "空召回表示没有召回任何资料，是 RAG 链路需要优先修复的问题。",
    }


def build_case_insight(result: dict[str, Any]) -> dict[str, Any]:
    empty_recall = int(result.get("emptyRecall") or 0) == 1
    hit_at_k = int(result.get("hitAtK") or 0) == 1
    metadata_match = int(result.get("metadataMatch") or 0) == 1
    keyword_coverage = float(result.get("keywordCoverage") or 0.0)
    top_titles = [str(item) for item in result.get("topTitles") or [] if str(item)]
    evidence = "；".join(top_titles[:3]) or "暂无 top 命中"

    if empty_recall:
        level = "miss"
        summary = "本 case 没有召回任何资料，需要优先检查 query、知识库数据和检索器。"
        action = "补充 seed 数据，检查检索 query，并确认知识库类型是否正确。"
    elif hit_at_k and metadata_match and keyword_coverage >= 0.5:
        level = "good"
        summary = "本 case 命中预期资料，metadata 和关键词覆盖也较稳定。"
        action = "保持当前样例，后续可增加更难的相似问题验证鲁棒性。"
    else:
        level = "weak"
        summary = "本 case 未命中预期资料或关键词覆盖不足，说明召回质量仍需优化。"
        action = "补充 seed 数据，优化 expectedKeywords，或改进 query rewrite 与 metadata filter。"

    return {
        "caseId": result.get("caseId"),
        "query": result.get("query"),
        "level": level,
        "summary": summary,
        "action": action,
        "evidence": evidence,
        "metrics": {
            "hitAtK": result.get("hitAtK", 0),
            "mrr": result.get("reciprocalRank", 0.0),
            "keywordCoverage": result.get("keywordCoverage", 0.0),
            "metadataMatch": result.get("metadataMatch", 0),
            "emptyRecall": result.get("emptyRecall", 0),
        },
    }
```

- [ ] **Step 4: Run explanation tests**

Run:

```powershell
python -m pytest tests/test_rag_evaluation_explanations.py tests/test_rag_evaluation.py -q
```

Expected: PASS.

- [ ] **Step 5: Create Stage 1B learning document**

Create `docs/learning/02-RAG质量评估指标HitK-MRR-关键词覆盖率.md` with:

```markdown
# 02 RAG 质量评估指标：Hit@K、MRR、关键词覆盖率

## 1. Hit@K

Hit@K 关注前 K 条召回结果里有没有命中预期资料。它回答的是：检索有没有找对方向。

## 2. MRR

MRR 关注正确资料排在第几位。第一条就是正确资料时分数高，第三条才出现时分数会低。

## 3. 关键词覆盖率

关键词覆盖率关注召回内容覆盖了多少预期关键词。它能帮助判断命中的资料是不是只“看起来相关”，还是确实覆盖了评分点。

## 4. metadataMatch

metadataMatch 判断知识库、岗位标签、面试阶段是否匹配，能避免把候选人画像、题库和岗位知识库混在一起。

## 5. emptyRecall

emptyRecall 表示完全没有召回资料。它通常说明 query 构造、知识库数据或检索器配置存在问题。

## 6. 面试时怎么讲

我给 RAG 做了固定评估集，每条 case 有 query、预期标题、预期关键词和 metadata 约束。评估时用 Hit@K 看有没有命中，用 MRR 看正确资料排得靠不靠前，用关键词覆盖率看内容是否覆盖关键评分点，再结合 metadataMatch 和 emptyRecall 定位召回问题。
```

---

## Stage 1C: RAG Observability Frontend

### Task 1.4: Expose Debug Explanations From Backend

**Files:**
- Modify: `backend_python/rag_explain.py`
- Modify: `backend_python/routes/rag.py`
- Modify: `tests/test_rag_debug_quality.py`

- [ ] **Step 1: Write failing API test**

In `tests/test_rag_debug_quality.py`, add a test asserting `/api/rag/debug` contains an `explanations` object:

```python
def test_rag_debug_returns_explanations(auth_client, monkeypatch) -> None:
    def fake_role_context(profile, stage, limit=5, db=None, user_id=None):
        return [
            {
                "title": "RAG 质量评估与可观测面板",
                "content": "Hit@K、MRR、关键词覆盖率用于评估 RAG 召回质量。",
                "score": 9,
                "matchedKeywords": ["Hit@K", "MRR", "关键词覆盖率"],
                "metadata": {"positionTag": "ai_app_intern", "interviewStage": "RAG 评估"},
            }
        ]

    monkeypatch.setattr("backend_python.routes.rag.retrieve_role_context", fake_role_context)
    monkeypatch.setattr("backend_python.routes.rag.retrieve_questions", lambda *args, **kwargs: [])
    monkeypatch.setattr("backend_python.routes.rag.retrieve_candidate_memory", lambda *args, **kwargs: [])

    response = auth_client.get(
        "/api/rag/debug",
        params={"role": "AI 应用开发实习生", "jd": "RAG 质量评估", "stage": "RAG 评估"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["explanations"]["roleKnowledge"]["hitCount"] == 1
    assert "RAG 质量评估与可观测面板" in data["explanations"]["roleKnowledge"]["topTitles"]
    assert "Hit@K" in data["explanations"]["roleKnowledge"]["matchedTerms"]
    assert data["explanations"]["roleKnowledge"]["qualityLevel"] == "good"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_rag_debug_quality.py::test_rag_debug_returns_explanations -q
```

Expected: FAIL because `/api/rag/debug` does not yet return `explanations`.

- [ ] **Step 3: Implement explanation helper**

Add to `backend_python/rag_explain.py`:

```python
def build_rag_debug_explanation(
    *,
    retriever_name: str,
    hits: list[dict[str, Any]],
    quality: dict[str, Any],
    limit: int = 3,
) -> dict[str, Any]:
    normalized_hits = [normalize_rag_hit(hit, retriever_name=retriever_name) for hit in hits[:limit]]
    matched_terms: list[str] = []
    for hit in normalized_hits:
        for key in ("matchedTokens", "matchedKeywords", "matchedTags"):
            for item in hit.get(key) or []:
                text = str(item)
                if text and text not in matched_terms:
                    matched_terms.append(text)

    top_titles = [str(hit.get("title") or hit.get("question") or "未命名命中") for hit in normalized_hits]
    return {
        "retrieverName": retriever_name,
        "retrieverLabel": retriever_label(retriever_name),
        "hitCount": len(hits),
        "qualityLevel": quality.get("level", "miss"),
        "qualityLabel": quality.get("label", "未评估"),
        "qualityReason": quality.get("reason", "暂无质量说明"),
        "topTitles": top_titles,
        "matchedTerms": matched_terms[:8],
        "developerSummary": (
            f"{retriever_label(retriever_name)}命中 {len(hits)} 条，"
            f"质量为{quality.get('label', '未评估')}，"
            f"主要命中：{'、'.join(top_titles[:2]) or '暂无'}。"
        ),
    }
```

- [ ] **Step 4: Wire helper into `/api/rag/debug`**

In `backend_python/routes/rag.py`, import `build_rag_debug_explanation` and compute quality once:

```python
from ..rag_explain import build_rag_debug_explanation
```

Then inside `debug_rag`, before `return`:

```python
quality = {
    "roleKnowledge": evaluate_retrieval_quality(role_hits),
    "questionBank": evaluate_retrieval_quality(question_hits),
    "candidateMemory": evaluate_retrieval_quality(candidate_memory),
}
explanations = {
    "roleKnowledge": build_rag_debug_explanation(
        retriever_name="role_knowledge", hits=role_hits, quality=quality["roleKnowledge"]
    ),
    "questionBank": build_rag_debug_explanation(
        retriever_name="question_bank", hits=question_hits, quality=quality["questionBank"]
    ),
    "candidateMemory": build_rag_debug_explanation(
        retriever_name="candidate_memory", hits=candidate_memory, quality=quality["candidateMemory"]
    ),
}
```

Return both `quality` and `explanations`.

- [ ] **Step 5: Run API tests**

Run:

```powershell
python -m pytest tests/test_rag_debug_quality.py tests/test_rag_explain.py -q
```

Expected: PASS.

### Task 1.5: Render RAG Debug Explanations In Frontend

**Files:**
- Modify: `tests/frontend_rag_quality.test.mjs`
- Modify: `app.js`
- Modify: `styles.css`
- Create: `docs/learning/03-RAG可观测面板怎么设计.md`

- [ ] **Step 1: Write failing frontend test**

Modify the mocked `/api/rag/debug` payload in `tests/frontend_rag_quality.test.mjs` to include:

```js
explanations: {
  roleKnowledge: {
    retrieverLabel: "岗位知识库",
    hitCount: 1,
    qualityLabel: "命中良好",
    topTitles: ["RAG 质量评估与可观测面板"],
    matchedTerms: ["Hit@K", "MRR", "关键词覆盖率"],
    developerSummary: "岗位知识库命中 1 条，质量为命中良好，主要命中：RAG 质量评估与可观测面板。"
  }
}
```

Add assertions:

```js
assert.match(getElement("#ragDebugContent").innerHTML, /RAG 命中解释/);
assert.match(getElement("#ragDebugContent").innerHTML, /岗位知识库命中 1 条/);
assert.match(getElement("#ragDebugContent").innerHTML, /Hit@K/);
assert.match(getElement("#ragDebugContent").innerHTML, /MRR/);
assert.doesNotMatch(getElement("#ragDebugContent").innerHTML, /undefined/);
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```powershell
node tests/frontend_rag_quality.test.mjs
```

Expected: FAIL because the frontend does not yet render `explanations`.

- [ ] **Step 3: Add render helper in `app.js`**

Add near `renderQualityOverview`:

```js
function renderRagExplanationPanel(explanations = {}) {
  const items = Object.values(explanations).filter(Boolean);
  if (!items.length) {
    return "";
  }
  return `
    <section class="rag-explanation-panel">
      <h3>RAG 命中解释</h3>
      <div class="rag-explanation-grid">
        ${items
          .map(
            (item) => `
              <article class="rag-explanation-card">
                <strong>${item.retrieverLabel || item.retrieverName || "RAG"}</strong>
                <p>${item.developerSummary || "暂无命中解释"}</p>
                <small>命中词：${(item.matchedTerms || []).join("、") || "未记录"}</small>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}
```

Then in `loadRagDebug`, render it after `renderQualityOverview`:

```js
${renderRagExplanationPanel(result.explanations || {})}
```

- [ ] **Step 4: Add CSS**

Add to `styles.css`:

```css
.rag-explanation-panel {
  display: grid;
  gap: 12px;
  grid-column: 1 / -1;
}

.rag-explanation-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.rag-explanation-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}

.rag-explanation-card strong,
.rag-explanation-card small {
  display: block;
}

.rag-explanation-card p,
.rag-explanation-card small {
  color: var(--muted);
  line-height: 1.6;
}

@media (max-width: 980px) {
  .rag-explanation-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
node tests/frontend_rag_quality.test.mjs
node tests/frontend_workbench_layout.test.mjs
```

Expected: PASS.

- [ ] **Step 6: Create Stage 1C learning document**

Create `docs/learning/03-RAG可观测面板怎么设计.md`:

```markdown
# 03 RAG 可观测面板怎么设计

## 1. 为什么要做 RAG 可观测

RAG 如果只把资料塞进 prompt，开发者很难知道模型为什么这样问。可观测面板可以展示 query、命中数量、命中资料、关键词和质量等级。

## 2. 普通用户和开发者看到的内容有什么不同

普通用户需要看到“为什么系统这样问”；开发者需要看到 retriever、hitCount、quality、matchedTerms 和 topTitles。

## 3. 本项目怎么做

后端 `/api/rag/debug` 返回三类 RAG 的 hits、quality 和 explanations。前端把 explanations 渲染成 RAG 命中解释卡片，避免用户直接阅读大段 JSON。

## 4. 面试时怎么讲

我把 RAG 调试信息从后端 JSON 转成前端可读面板，能看到每个 retriever 命中了几条、质量如何、主要命中哪些资料和关键词。这样可以排查为什么面试官问这个问题，也能定位召回不准的问题。
```

---

## Stage 2A: Agent V3 Preparation If Time Allows

### Task 2.1: Write Agent V3 Design And Learning Document

**Files:**
- Create: `docs/superpowers/specs/2026-06-10-agent-engineering-v3-design.md`
- Create: `docs/learning/04-Agent状态决策工具日志完整讲解.md`

- [ ] **Step 1: Create Agent V3 spec**

Create a design doc with sections:

```markdown
# Agent 工程化 V3 设计

## 1. 目标

把现有 Interview Orchestrator Agent 整理成更接近企业 AI 应用的状态机结构，但本阶段不引入 LangGraph。

## 2. 节点模型

- observe_state：收集 profile、history、lastAnswer、roundCount、remainingRounds。
- analyze_answer：判断回答是否完整、偏弱、重复或跑题。
- retrieve_context：调用三类 RAG。
- select_action：选择 deep_dive、lower_difficulty、switch_topic、end_interview。
- generate_question：结合决策和上下文生成问题。
- update_memory：把关键回答和弱点写入候选人画像。

## 3. 与 LangGraph 的映射

这些节点未来可以映射为 StateGraph node，Agent State 可以作为 graph state，checkpoint 可用于恢复多轮面试状态。

## 4. 非目标

不安装 LangGraph，不重写现有 Agent，不破坏 `/api/interview/next-question`。
```

- [ ] **Step 2: Create Agent learning document**

Create `docs/learning/04-Agent状态决策工具日志完整讲解.md` with:

```markdown
# 04 Agent 状态、决策、工具和日志完整讲解

## 1. Agent 和普通 LLM 调用的区别

普通 LLM 调用是输入 prompt 得到回答。Agent 会围绕目标维护状态、调用工具、观察结果，再决定下一步动作。

## 2. 本项目里的 Agent State

Agent State 包含 profile、历史问答、上一轮回答、三个 RAG 命中结果、retrievalQuality、轮次和剩余轮次。

## 3. Tool Calls

三个 RAG 可以看作工具调用：岗位知识库、题库 RAG、候选人画像 RAG。

## 4. Agent Decision

Agent Decision 决定下一步是深挖、降难度、切换话题还是结束。

## 5. fallback、normalize、guardrail

fallback 提供规则兜底，normalize 校验模型输出字段，guardrail 防止重复追问和无意义卡死。

## 6. 面试时怎么讲

我的项目不是简单聊天，而是 Orchestrator Agent。它会根据用户回答、历史记录、RAG 召回和剩余轮次做决策，并把决策过程记录到日志和调试面板中。
```

---

## Stage 3 And 4 Candidate Tasks

These tasks run only after Stage 0, Stage 1A, Stage 1B, Stage 1C, and Stage 2A have meaningful outputs.

### Task 3.1: Training Loop Document

**Files:**
- Create: `docs/learning/05-AI模拟面试训练闭环怎么讲.md`

Create a learning document explaining question reviews, weak topics, retry questions, next-round priority, and coach/interview mode differences.

### Task 4.1: Pre-Deployment Checklist

**Files:**
- Create: `docs/learning/06-上线部署前置知识与准备清单.md`
- Create: `docs/deployment-preflight-checklist.md`

Create deployment-preparation documents explaining Uvicorn, Nginx, Redis, database migration, environment variables, logs, backups, and what remains before real cloud deployment.

---

## Full Verification

Run after every code phase:

```powershell
python -m pytest -q
```

Run after frontend changes:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Run browser verification after frontend UI changes:

```text
http://127.0.0.1:8000/
```

Expected browser checks:

- Page opens.
- No visible horizontal overflow on desktop and mobile.
- No `undefined`.
- Console has no error.
- RAG debug panel shows quality and explanation summaries.

---

## Self-Review

- Spec coverage:
  - Stage 0 baseline: Task 0.1.
  - Stage 1A seed and evaluation cases: Task 1.1, Task 1.2.
  - Stage 1B metrics and explanations: Task 1.3.
  - Stage 1C frontend observability: Task 1.4, Task 1.5.
  - Stage 2A Agent V3 preparation: Task 2.1.
  - Stage 3/4 candidate tasks: Task 3.1, Task 4.1.
- Scope check:
  - No Docker/Nginx/cloud deployment implementation.
  - No LangGraph/LangChain dependency.
  - No React/Vue/Next migration.
  - No admin backend.
- Unfilled-content scan:
  - No empty sections.
  - Candidate tasks are intentionally gated after the required phases.
- Type consistency:
  - Uses existing `knowledgeBase`, `expectedKnowledgeBase`, `expectedPositionTag`, `expectedStage`, `expectedTitle`, `expectedKeywords`.
  - Frontend uses existing `ragDebugContent`, `loadRagDebug`, and debug panel patterns.
