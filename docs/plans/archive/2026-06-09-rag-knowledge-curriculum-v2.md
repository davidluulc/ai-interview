# RAG Knowledge Curriculum V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first V2 knowledge batch for AI 应用开发岗 and Python 后端岗 by adding data quality tests, role knowledge seed entries, question bank entries, RAG evaluation cases, and evaluation seed documents.

**Architecture:** This plan keeps the existing lightweight RAG architecture. It expands JSON seed data and evaluation fixtures without changing public APIs, frontend structure, vector database dependencies, or Agent decision logic. Data quality is enforced through pytest before adding content, so future knowledge expansion stays maintainable.

**Tech Stack:** Python, pytest, JSON seed files, FastAPI project structure, existing RAG retrieval and evaluation modules.

---

## 0. Scope And Learning Point

本轮要学的是：**RAG 的质量不只取决于检索算法，也取决于知识库内容质量和评估数据集质量。**

本轮不做：

- 不改前端页面。
- 不改后端 API。
- 不引入 LangGraph / LangChain。
- 不引入新向量数据库。
- 不做 Docker / Nginx / 云服务器上线。
- 不把 Python 后端和 AI 应用开发所有知识一次性写成百科。

本轮只做：

- 给 seed 数据增加质量测试。
- 给 `data/role_knowledge_seed.json` 新增 20 条高质量岗位知识。
- 给 `data/question_bank_seed.json` 新增 20 条高质量题库问题。
- 给 `data/rag_evaluation_cases.json` 新增 20 条评估 case。
- 给 `backend_python/rag_evaluation_seed.py` 新增对应评估 seed 文档。
- 必要时更新 `scripts/run_rag_evaluation.py` 的 mock embedding 映射。

## 1. File Structure

Create:

```text
tests/test_rag_knowledge_curriculum_v2.py
```

Modify:

```text
data/role_knowledge_seed.json
data/question_bank_seed.json
data/rag_evaluation_cases.json
backend_python/rag_evaluation_seed.py
scripts/run_rag_evaluation.py
```

Do not modify:

```text
backend_python/routes/
backend_python/agent_*.py
backend_python/interview_agent.py
app.js
styles.css
index.html
```

## 2. Required V2 Topics

### 2.1 Python 后端岗 10 个 role knowledge 主题

Use these exact IDs:

| id | title | category | must include keywords |
| --- | --- | --- | --- |
| `py_backend_v2_python_async` | Python async/await 与后端 I/O | Python 基础 | `async`, `await`, `I/O`, `并发`, `FastAPI` |
| `py_backend_v2_http_status` | HTTP 请求响应与状态码 | Web 后端基础 | `HTTP`, `状态码`, `请求`, `响应`, `422` |
| `py_backend_v2_fastapi_depends` | FastAPI Depends 依赖注入 | FastAPI | `Depends`, `依赖注入`, `get_db`, `get_current_user` |
| `py_backend_v2_pydantic_schema` | Pydantic Schema 与接口校验 | FastAPI | `Pydantic`, `schema`, `校验`, `422` |
| `py_backend_v2_sqlalchemy_relationship` | SQLAlchemy 外键与 relationship | 数据库 | `ForeignKey`, `relationship`, `user_id`, `一对多` |
| `py_backend_v2_transaction_alembic` | 数据库事务与 Alembic 迁移 | 数据库 | `事务`, `commit`, `rollback`, `Alembic` |
| `py_backend_v2_jwt_refresh_token` | JWT 双 token 认证方案 | 鉴权 | `JWT`, `access token`, `refresh token`, `退出登录` |
| `py_backend_v2_user_data_isolation` | 用户数据隔离与权限边界 | 鉴权 | `current_user`, `user_id`, `权限`, `隔离` |
| `py_backend_v2_logging_testing` | 后端日志与 pytest 测试 | 工程化 | `日志`, `pytest`, `统一错误`, `测试` |
| `py_backend_v2_uvicorn_nginx_deploy` | Uvicorn、Nginx 与云服务器部署关系 | 部署 | `Uvicorn`, `Nginx`, `反向代理`, `云服务器` |

### 2.2 AI 应用开发岗 10 个 role knowledge 主题

Use these exact IDs:

| id | title | category | must include keywords |
| --- | --- | --- | --- |
| `ai_app_v2_llm_api_params` | 大模型 API 调用与参数调优 | 模型调用 | `temperature`, `JSON`, `超时`, `重试` |
| `ai_app_v2_prompt_template` | Prompt 模板化与结构化输出 | Prompt 工程 | `prompt`, `模板`, `结构化输出`, `few-shot` |
| `ai_app_v2_rag_pipeline` | RAG 从文档到 prompt 的完整链路 | RAG | `query`, `chunk`, `metadata`, `prompt` |
| `ai_app_v2_bm25_vector_hybrid` | BM25、向量检索与 Hybrid Search | RAG | `BM25`, `embedding`, `vector`, `hybrid` |
| `ai_app_v2_rerank_eval` | Rerank 与 RAG 质量评估 | RAG 评估 | `rerank`, `Hit@K`, `MRR`, `关键词覆盖率` |
| `ai_app_v2_three_rags_boundary` | 三类 RAG 的职责边界 | RAG 架构 | `岗位知识库`, `题库`, `候选人画像`, `权限隔离` |
| `ai_app_v2_agent_state_decision` | Agent State 与 Agent Decision | Agent | `Agent State`, `Agent Decision`, `状态`, `决策` |
| `ai_app_v2_toolcalls_trace` | ToolCalls、nodeTrace 与可观测性 | Agent 工程化 | `ToolCalls`, `nodeTrace`, `日志`, `可观测` |
| `ai_app_v2_guardrails_fallback` | Guardrails、normalize 与 fallback | Agent 兜底 | `guardrails`, `normalize`, `fallback`, `JSON 校验` |
| `ai_app_v2_frontier_langgraph_mcp` | LangGraph、MCP 与 Agents SDK 前沿方向 | 前沿方向 | `LangGraph`, `MCP`, `tools`, `checkpoint` |

### 2.3 Python 后端岗 10 个 question bank 主题

Use IDs `qb_py_v2_001` through `qb_py_v2_010`.

| id | difficulty | category | question intent |
| --- | --- | --- | --- |
| `qb_py_v2_001` | basic | technical | 解释 Python async/await 为什么适合高并发 I/O |
| `qb_py_v2_002` | basic | technical | 解释 HTTP 请求响应和 422 状态码 |
| `qb_py_v2_003` | medium | technical | 解释 FastAPI Depends(get_db) 和 Depends(get_current_user) |
| `qb_py_v2_004` | medium | technical | 解释 Pydantic schema 在接口里的作用 |
| `qb_py_v2_005` | medium | technical | 用 interview_records 举例解释 ForeignKey 和 relationship |
| `qb_py_v2_006` | medium | technical | 解释 SQLAlchemy Session、commit、rollback |
| `qb_py_v2_007` | medium | technical | 讲 JWT access token + refresh token 流程 |
| `qb_py_v2_008` | hard | scenario | 如何避免用户 A 查到用户 B 的面试记录 |
| `qb_py_v2_009` | medium | project | 如何排查 FastAPI 接口 422 或 500 |
| `qb_py_v2_010` | medium | technical | 解释 Uvicorn、Nginx、云服务器关系 |

### 2.4 AI 应用开发岗 10 个 question bank 主题

Use IDs `qb_ai_v2_001` through `qb_ai_v2_010`.

| id | difficulty | category | question intent |
| --- | --- | --- | --- |
| `qb_ai_v2_001` | basic | technical | 解释 temperature、JSON 输出、超时重试 |
| `qb_ai_v2_002` | medium | project | 讲 AI 模拟面试系统的模型调用链路 |
| `qb_ai_v2_003` | medium | technical | 解释 RAG 从 query 到 prompt 的链路 |
| `qb_ai_v2_004` | medium | technical | 对比 BM25 和向量检索 |
| `qb_ai_v2_005` | hard | technical | 解释 hybrid search 和 rerank 的关系 |
| `qb_ai_v2_006` | medium | project | 为什么设计三个 RAG，而不是一个 RAG |
| `qb_ai_v2_007` | medium | technical | Agent State 里应该包含什么 |
| `qb_ai_v2_008` | medium | technical | ToolCalls 是什么，和工具本身有什么区别 |
| `qb_ai_v2_009` | hard | scenario | 模型输出非法 decision 时如何 normalize/fallback |
| `qb_ai_v2_010` | hard | technical | 为什么当前不直接上 LangGraph，未来怎么迁移 |

## 3. Task 1: Add V2 Seed Data Quality Tests

**Files:**

- Create: `tests/test_rag_knowledge_curriculum_v2.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/test_rag_knowledge_curriculum_v2.py` with this exact content:

```python
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLE_PATH = ROOT / "data" / "role_knowledge_seed.json"
QUESTION_PATH = ROOT / "data" / "question_bank_seed.json"
CASE_PATH = ROOT / "data" / "rag_evaluation_cases.json"

PY_ROLE_IDS = {
    "py_backend_v2_python_async",
    "py_backend_v2_http_status",
    "py_backend_v2_fastapi_depends",
    "py_backend_v2_pydantic_schema",
    "py_backend_v2_sqlalchemy_relationship",
    "py_backend_v2_transaction_alembic",
    "py_backend_v2_jwt_refresh_token",
    "py_backend_v2_user_data_isolation",
    "py_backend_v2_logging_testing",
    "py_backend_v2_uvicorn_nginx_deploy",
}

AI_ROLE_IDS = {
    "ai_app_v2_llm_api_params",
    "ai_app_v2_prompt_template",
    "ai_app_v2_rag_pipeline",
    "ai_app_v2_bm25_vector_hybrid",
    "ai_app_v2_rerank_eval",
    "ai_app_v2_three_rags_boundary",
    "ai_app_v2_agent_state_decision",
    "ai_app_v2_toolcalls_trace",
    "ai_app_v2_guardrails_fallback",
    "ai_app_v2_frontier_langgraph_mcp",
}

PY_QUESTION_IDS = {f"qb_py_v2_{index:03d}" for index in range(1, 11)}
AI_QUESTION_IDS = {f"qb_ai_v2_{index:03d}" for index in range(1, 11)}
PY_EVAL_IDS = {f"eval_py_backend_v2_{index:03d}" for index in range(1, 11)}
AI_EVAL_IDS = {f"eval_ai_app_v2_{index:03d}" for index in range(1, 11)}


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_unique_ids(items: list[dict], key: str = "id") -> None:
    counts = Counter(str(item.get(key) or "") for item in items)
    duplicates = sorted(item_id for item_id, count in counts.items() if count > 1)
    assert not duplicates


def test_role_knowledge_v2_entries_exist_and_are_complete() -> None:
    items = load_json(ROLE_PATH)
    assert_unique_ids(items)
    by_id = {item["id"]: item for item in items}

    assert PY_ROLE_IDS.issubset(by_id)
    assert AI_ROLE_IDS.issubset(by_id)

    for item_id in PY_ROLE_IDS | AI_ROLE_IDS:
        item = by_id[item_id]
        assert item["role"] in {"Python 后端开发实习生", "AI 应用开发实习生"}
        assert item["category"]
        assert item["title"]
        assert isinstance(item["keywords"], list) and len(item["keywords"]) >= 5
        assert len(item["content"]) >= 80
        assert isinstance(item["follow_up_questions"], list) and len(item["follow_up_questions"]) >= 3
        assert isinstance(item["scoring_points"], list) and len(item["scoring_points"]) >= 4
        assert isinstance(item["risk_signals"], list) and len(item["risk_signals"]) >= 3


def test_question_bank_v2_entries_exist_and_are_complete() -> None:
    items = load_json(QUESTION_PATH)
    assert_unique_ids(items)
    by_id = {item["id"]: item for item in items}

    assert PY_QUESTION_IDS.issubset(by_id)
    assert AI_QUESTION_IDS.issubset(by_id)

    for item_id in PY_QUESTION_IDS:
        item = by_id[item_id]
        assert item["position_tag"] == "python_backend_intern"
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert item["question"]
        assert len(item["reference_answer"]) >= 50
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4

    for item_id in AI_QUESTION_IDS:
        item = by_id[item_id]
        assert item["position_tag"] == "ai_app_intern"
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert item["question"]
        assert len(item["reference_answer"]) >= 50
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4


def test_rag_evaluation_v2_cases_exist_and_are_complete() -> None:
    cases = load_json(CASE_PATH)
    assert_unique_ids(cases)
    by_id = {item["id"]: item for item in cases}

    assert PY_EVAL_IDS.issubset(by_id)
    assert AI_EVAL_IDS.issubset(by_id)

    for case_id in PY_EVAL_IDS:
        case = by_id[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedPositionTag"] == "python_backend_intern"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4

    for case_id in AI_EVAL_IDS:
        case = by_id[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedPositionTag"] == "ai_app_intern"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_rag_knowledge_curriculum_v2.py -q
```

Expected:

```text
FAILED ... PY_ROLE_IDS.issubset(by_id)
```

or a similar failure showing the V2 entries do not exist yet.

Do not edit production data before observing this failure.

## 4. Task 2: Add Role Knowledge Seed Entries

**Files:**

- Modify: `data/role_knowledge_seed.json`
- Test: `tests/test_rag_knowledge_curriculum_v2.py`

- [ ] **Step 1: Append the 20 role knowledge records**

Append one JSON object for each ID listed in section 2.1 and 2.2.

Each Python backend record must use:

```json
"role": "Python 后端开发实习生"
```

Each AI app record must use:

```json
"role": "AI 应用开发实习生"
```

Use this object shape for every record:

```json
{
  "id": "py_backend_v2_fastapi_depends",
  "role": "Python 后端开发实习生",
  "category": "FastAPI",
  "title": "FastAPI Depends 依赖注入",
  "keywords": ["FastAPI", "Depends", "依赖注入", "get_db", "get_current_user", "数据库会话", "鉴权"],
  "content": "FastAPI 的 Depends 用来把公共能力注入到路由函数中，例如数据库会话、当前登录用户、公共参数和权限校验。本项目中 Depends(get_db) 负责提供 SQLAlchemy Session，Depends(get_current_user) 负责解析 token 并拿到当前用户。这样接口函数不用手动创建数据库连接，也能保证受保护接口具备鉴权能力。",
  "follow_up_questions": [
    "Depends(get_db) 和 Depends(get_current_user) 分别解决什么问题？",
    "为什么数据库会话不应该在每个接口里手动创建？",
    "如果一个接口忘记加 get_current_user，会带来什么风险？"
  ],
  "scoring_points": [
    "能说明 Depends 是依赖注入机制",
    "能结合 get_db 解释数据库会话注入",
    "能结合 get_current_user 解释鉴权注入",
    "能说明依赖注入对复用和测试的价值"
  ],
  "risk_signals": [
    "只会说 Depends 是传参",
    "分不清数据库会话和用户鉴权",
    "不知道缺少鉴权依赖会导致越权访问"
  ]
}
```

For the other 19 records, write content with the same detail level and include all required keywords from section 2.

- [ ] **Step 2: Verify JSON parses**

Run:

```powershell
@'
import json
from pathlib import Path
json.loads(Path("data/role_knowledge_seed.json").read_text(encoding="utf-8"))
print("role knowledge json ok")
'@ | python -
```

Expected:

```text
role knowledge json ok
```

- [ ] **Step 3: Run role knowledge V2 test**

Run:

```powershell
python -m pytest tests/test_rag_knowledge_curriculum_v2.py::test_role_knowledge_v2_entries_exist_and_are_complete -q
```

Expected:

```text
1 passed
```

## 5. Task 3: Add Question Bank Seed Entries

**Files:**

- Modify: `data/question_bank_seed.json`
- Test: `tests/test_rag_knowledge_curriculum_v2.py`

- [ ] **Step 1: Append the 20 question bank records**

Append records for `qb_py_v2_001` through `qb_py_v2_010` and `qb_ai_v2_001` through `qb_ai_v2_010`.

Use this object shape:

```json
{
  "id": "qb_py_v2_003",
  "category": "technical",
  "position_tag": "python_backend_intern",
  "difficulty": "medium",
  "question": "FastAPI 中 Depends(get_db) 和 Depends(get_current_user) 分别解决什么问题？",
  "reference_answer": "Depends(get_db) 用来为接口注入数据库会话，避免每个接口手动创建和关闭连接；Depends(get_current_user) 用来解析请求中的 token，拿到当前登录用户并保护接口权限。它们体现了依赖注入思想，把数据库访问和鉴权这种公共能力从业务接口里抽离出来。",
  "key_points": ["Depends", "依赖注入", "数据库会话", "当前用户", "鉴权"],
  "tags": ["FastAPI", "Depends", "get_db", "get_current_user", "后端结构"]
}
```

Every record must satisfy:

- `reference_answer` length >= 50 Chinese characters.
- `key_points` length >= 4.
- `tags` length >= 4.
- Python records use `position_tag: "python_backend_intern"`.
- AI records use `position_tag: "ai_app_intern"`.

- [ ] **Step 2: Verify JSON parses**

Run:

```powershell
@'
import json
from pathlib import Path
json.loads(Path("data/question_bank_seed.json").read_text(encoding="utf-8"))
print("question bank json ok")
'@ | python -
```

Expected:

```text
question bank json ok
```

- [ ] **Step 3: Run question bank V2 test**

Run:

```powershell
python -m pytest tests/test_rag_knowledge_curriculum_v2.py::test_question_bank_v2_entries_exist_and_are_complete -q
```

Expected:

```text
1 passed
```

## 6. Task 4: Add RAG Evaluation Cases And Evaluation Seed Documents

**Files:**

- Modify: `data/rag_evaluation_cases.json`
- Modify: `backend_python/rag_evaluation_seed.py`
- Modify: `scripts/run_rag_evaluation.py`
- Test: `tests/test_rag_knowledge_curriculum_v2.py`
- Test: `tests/test_rag_evaluation.py`
- Test: `tests/test_rag_evaluation_seed.py`
- Test: `tests/test_rag_evaluation_script.py`

- [ ] **Step 1: Append 20 evaluation cases**

Append case IDs:

```text
eval_py_backend_v2_001 ... eval_py_backend_v2_010
eval_ai_app_v2_001 ... eval_ai_app_v2_010
```

Each case must use:

```json
"knowledgeBase": "role_knowledge"
```

Python backend cases must use:

```json
"expectedPositionTag": "python_backend_intern"
```

AI app cases must use:

```json
"expectedPositionTag": "ai_app_intern"
```

Example case:

```json
{
  "id": "eval_py_backend_v2_003",
  "query": "FastAPI Depends(get_db) 和 Depends(get_current_user) 分别是什么？",
  "knowledgeBase": "role_knowledge",
  "expectedKnowledgeBase": "role_knowledge",
  "expectedPositionTag": "python_backend_intern",
  "expectedStage": "技术基础",
  "expectedTitle": "FastAPI Depends 依赖注入",
  "expectedKeywords": ["Depends", "依赖注入", "get_db", "get_current_user"]
}
```

- [ ] **Step 2: Add matching evaluation seed documents**

In `backend_python/rag_evaluation_seed.py`, extend `EVALUATION_SEED_DOCUMENTS` with documents matching the 20 evaluation cases.

Each new document must include:

```python
{
    "caseId": "eval_py_backend_v2_003",
    "knowledgeBase": "role_knowledge",
    "title": "FastAPI Depends 依赖注入",
    "content": "FastAPI Depends 用于依赖注入，Depends(get_db) 注入数据库会话，Depends(get_current_user) 注入当前登录用户和鉴权能力。",
    "metadata": {
        "category": "technical",
        "caseId": "eval_py_backend_v2_003",
        "positionTag": "python_backend_intern",
        "interviewStage": "技术基础"
    },
    "embedding": [0.0, 1.0, 0.0],
}
```

Use deterministic 3-dimensional embeddings. It is acceptable to reuse these vectors by topic:

```python
[1.0, 0.0, 0.0]  # LLM / RAG / AI application
[0.0, 1.0, 0.0]  # Python backend / FastAPI / database
[0.0, 0.0, 1.0]  # Agent / trace / orchestration
[0.7, 0.7, 0.0]  # Hybrid backend + AI topics
[0.7, 0.0, 0.7]  # RAG + Agent topics
```

- [ ] **Step 3: Update mock query embeddings**

In `scripts/run_rag_evaluation.py`, extend `MOCK_QUERY_EMBEDDINGS` for the new evaluation case IDs.

Example:

```python
MOCK_QUERY_EMBEDDINGS = {
    "rag_log_fields": [1.0, 0.0, 0.0],
    "fastapi_module_split": [0.0, 1.0, 0.0],
    "hybrid_search_reason": [0.7, 0.7, 0.0],
    "rerank_fallback": [0.6, 0.3, 0.7],
    "interview_follow_up": [0.2, 0.4, 0.9],
    "eval_py_backend_v2_001": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_002": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_003": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_004": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_005": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_006": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_007": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_008": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_009": [0.0, 1.0, 0.0],
    "eval_py_backend_v2_010": [0.0, 1.0, 0.0],
    "eval_ai_app_v2_001": [1.0, 0.0, 0.0],
    "eval_ai_app_v2_002": [1.0, 0.0, 0.0],
    "eval_ai_app_v2_003": [1.0, 0.0, 0.0],
    "eval_ai_app_v2_004": [0.7, 0.7, 0.0],
    "eval_ai_app_v2_005": [0.7, 0.7, 0.0],
    "eval_ai_app_v2_006": [0.7, 0.7, 0.0],
    "eval_ai_app_v2_007": [0.0, 0.0, 1.0],
    "eval_ai_app_v2_008": [0.0, 0.0, 1.0],
    "eval_ai_app_v2_009": [0.0, 0.0, 1.0],
    "eval_ai_app_v2_010": [0.7, 0.0, 0.7],
}
```

- [ ] **Step 4: Run evaluation data tests**

Run:

```powershell
python -m pytest tests/test_rag_knowledge_curriculum_v2.py::test_rag_evaluation_v2_cases_exist_and_are_complete tests/test_rag_evaluation.py tests/test_rag_evaluation_seed.py tests/test_rag_evaluation_script.py -q
```

Expected:

```text
all selected tests passed
```

## 7. Task 5: Run Targeted Retrieval Smoke Checks

**Files:**

- No required file modifications.

- [ ] **Step 1: Run direct JSON loader smoke checks**

Run:

```powershell
@'
from backend_python.rag import load_role_knowledge
from backend_python.question_rag import load_question_bank

role_items = load_role_knowledge()
question_items = load_question_bank()

print("role_count", len(role_items))
print("question_count", len(question_items))
print("has_py_depends", any(item.get("id") == "py_backend_v2_fastapi_depends" for item in role_items))
print("has_ai_agent", any(item.get("id") == "ai_app_v2_agent_state_decision" for item in role_items))
print("has_qb_py", any(item.get("id") == "qb_py_v2_003" for item in question_items))
print("has_qb_ai", any(item.get("id") == "qb_ai_v2_007" for item in question_items))
'@ | python -
```

Expected output includes:

```text
has_py_depends True
has_ai_agent True
has_qb_py True
has_qb_ai True
```

- [ ] **Step 2: Run RAG evaluation script with mock vectors**

Run:

```powershell
python scripts/run_rag_evaluation.py --mock-vector
```

Expected:

```text
JSON output with modes bm25, vector, hybrid, hybrid_rerank and no traceback
```

## 8. Task 6: Full Verification

**Files:**

- No required file modifications.

- [ ] **Step 1: Run all backend tests**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
all backend tests passed
```

- [ ] **Step 2: Run all frontend .mjs tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
all frontend tests exit with code 0
```

- [ ] **Step 3: Inspect git diff**

Run:

```powershell
git diff -- data/role_knowledge_seed.json data/question_bank_seed.json data/rag_evaluation_cases.json backend_python/rag_evaluation_seed.py scripts/run_rag_evaluation.py tests/test_rag_knowledge_curriculum_v2.py
```

Expected:

```text
diff only includes seed data, evaluation fixtures, mock embedding map, and V2 tests
```

## 9. Task 7: Interview Explanation Notes

**Files:**

- Modify: `docs/ai-interview-project-learning-handbook.md`

- [ ] **Step 1: Add a short V2 knowledge base paragraph**

Add this paragraph under the RAG section:

```markdown
### RAG 知识体系 V2

这一阶段我把知识库建设拆成两层：第一层是岗位知识地图，用来尽量完整覆盖 Python 后端岗和 AI 应用开发岗从基础到进阶的知识范围；第二层是 RAG seed 数据和评估 case，只把高频、可追问、可评估、能改善当前面试体验的知识点分批落地。这样既能保证长期学习路线完整，也能避免一次性把知识库写成无法维护的百科全书。
```

- [ ] **Step 2: Verify the paragraph exists**

Run:

```powershell
Select-String -Path 'docs\ai-interview-project-learning-handbook.md' -Encoding utf8 -Pattern 'RAG 知识体系 V2'
```

Expected:

```text
one matching line
```

## 10. Completion Checklist

Before calling this phase done, verify:

- [ ] `tests/test_rag_knowledge_curriculum_v2.py` exists.
- [ ] `data/role_knowledge_seed.json` has all 20 V2 role knowledge IDs.
- [ ] `data/question_bank_seed.json` has all 20 V2 question IDs.
- [ ] `data/rag_evaluation_cases.json` has all 20 V2 evaluation case IDs.
- [ ] `backend_python/rag_evaluation_seed.py` has matching evaluation seed documents.
- [ ] `scripts/run_rag_evaluation.py --mock-vector` runs without traceback.
- [ ] `python -m pytest -q` passes.
- [ ] all frontend `.mjs` tests pass.
- [ ] No frontend page files were modified.
- [ ] No backend API routes were modified.

## 11. Suggested Commit

After all verification passes:

```powershell
git add data/role_knowledge_seed.json data/question_bank_seed.json data/rag_evaluation_cases.json backend_python/rag_evaluation_seed.py scripts/run_rag_evaluation.py tests/test_rag_knowledge_curriculum_v2.py docs/ai-interview-project-learning-handbook.md
git commit -m "feat: expand rag knowledge curriculum v2"
```

Do not commit `.env`, `data/app.db`, `__pycache__`, `.pytest_cache`, or unrelated files.

