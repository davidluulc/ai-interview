# RAG Evaluation V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个小型 RAG 质量评估工具，用固定评估集对比 BM25、Vector、Hybrid、Hybrid + Rerank 的 Hit@K、MRR 和关键词覆盖率。

**Architecture:** 使用 JSON 文件保存评估样例；新增 `backend_python/rag_evaluation.py` 负责指标计算和汇总；新增 `scripts/run_rag_evaluation.py` 负责读取样例、调用 `retrieve_chunks`、输出 JSON。V1 不建表、不做前端、不使用大模型裁判。

**Tech Stack:** Python, FastAPI project modules, SQLAlchemy Session, SQLite, pytest, JSON.

---

## File Structure

- Add: `data/rag_evaluation_cases.json`
  - 保存固定评估样例
- Add: `backend_python/rag_evaluation.py`
  - 指标计算、单 case 评估、按模式汇总
- Add: `scripts/run_rag_evaluation.py`
  - 命令行评估入口
- Add: `tests/test_rag_evaluation.py`
  - 覆盖 Hit@K、MRR、关键词覆盖率、模式汇总
- Add: `tests/test_rag_evaluation_script.py`
  - 覆盖脚本输出结构和失败隔离

## Task 1: Evaluation Case File

**Files:**
- Add: `data/rag_evaluation_cases.json`
- Add: `tests/test_rag_evaluation.py`

- [ ] Write the failing test for loading case structure.

```python
import json
from pathlib import Path


def test_rag_evaluation_cases_have_required_fields() -> None:
    path = Path("data/rag_evaluation_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))

    assert cases
    for item in cases:
        assert item["id"]
        assert item["query"]
        assert item["knowledgeBase"] in {"role_knowledge", "question_bank"}
        assert item["expectedTitle"]
        assert isinstance(item["expectedKeywords"], list)
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_evaluation.py::test_rag_evaluation_cases_have_required_fields -q
```

Expected: `data/rag_evaluation_cases.json` missing.

- [ ] Create the evaluation case file.

```json
[
  {
    "id": "rag_log_fields",
    "query": "RAG 命中日志应该记录哪些字段？",
    "knowledgeBase": "role_knowledge",
    "expectedTitle": "RAG 日志工程化",
    "expectedKeywords": ["query_text", "retriever_name", "hit_count", "quality"]
  },
  {
    "id": "fastapi_module_split",
    "query": "FastAPI 后端模块化一般怎么拆分？",
    "knowledgeBase": "role_knowledge",
    "expectedTitle": "FastAPI 模块化",
    "expectedKeywords": ["APIRouter", "routes", "service"]
  },
  {
    "id": "hybrid_search_reason",
    "query": "为什么 RAG 要做 BM25 和向量检索的混合召回？",
    "knowledgeBase": "role_knowledge",
    "expectedTitle": "Hybrid Search",
    "expectedKeywords": ["BM25", "vector", "归一化", "去重"]
  },
  {
    "id": "rerank_fallback",
    "query": "Rerank 模型失败时系统应该怎么处理？",
    "knowledgeBase": "role_knowledge",
    "expectedTitle": "Rerank 重排",
    "expectedKeywords": ["降级", "Hybrid", "rerankScore"]
  },
  {
    "id": "interview_follow_up",
    "query": "AI 面试官如何根据候选人回答继续追问？",
    "knowledgeBase": "question_bank",
    "expectedTitle": "面试追问策略",
    "expectedKeywords": ["追问", "回答", "项目细节"]
  }
]
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_evaluation.py::test_rag_evaluation_cases_have_required_fields -q
```

Expected: case file structure test passes.

## Task 2: Core Metric Functions

**Files:**
- Add: `backend_python/rag_evaluation.py`
- Modify: `tests/test_rag_evaluation.py`

- [ ] Write failing tests for Hit@K, reciprocal rank, and keyword coverage.

```python
from backend_python.rag_evaluation import (
    calculate_hit_at_k,
    calculate_keyword_coverage,
    calculate_reciprocal_rank,
)


def test_calculate_hit_at_k_detects_expected_title_in_top_k() -> None:
    hits = [
        {"title": "FastAPI 模块化", "content": "APIRouter routes service"},
        {"title": "RAG 日志工程化", "content": "query_text hit_count"},
    ]

    assert calculate_hit_at_k(hits, "RAG 日志工程化", ["quality"], 2) == 1
    assert calculate_hit_at_k(hits, "RAG 日志工程化", ["quality"], 1) == 0


def test_calculate_reciprocal_rank_uses_first_expected_hit_rank() -> None:
    hits = [
        {"title": "FastAPI 模块化", "content": "APIRouter"},
        {"title": "RAG 日志工程化", "content": "query_text"},
    ]

    assert calculate_reciprocal_rank(hits, "RAG 日志工程化", ["query_text"]) == 0.5


def test_calculate_keyword_coverage_uses_top_k_content() -> None:
    hits = [
        {"title": "RAG 日志工程化", "content": "query_text hit_count quality"},
        {"title": "其它", "content": "retriever_name"},
    ]

    assert calculate_keyword_coverage(hits, ["query_text", "retriever_name", "hit_count", "quality"], 1) == 0.75
    assert calculate_keyword_coverage(hits, ["query_text", "retriever_name", "hit_count", "quality"], 2) == 1.0
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_evaluation.py::test_calculate_hit_at_k_detects_expected_title_in_top_k tests/test_rag_evaluation.py::test_calculate_reciprocal_rank_uses_first_expected_hit_rank tests/test_rag_evaluation.py::test_calculate_keyword_coverage_uses_top_k_content -q
```

Expected: missing `backend_python.rag_evaluation`.

- [ ] Implement metric functions.

```python
from typing import Any


def normalize_text(value: object) -> str:
    return str(value or "").lower()


def hit_text(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata") or {}
    metadata_text = " ".join(str(value) for value in metadata.values())
    return " ".join([str(hit.get("title") or ""), str(hit.get("content") or ""), metadata_text])


def is_expected_hit(hit: dict[str, Any], expected_title: str, expected_keywords: list[str]) -> bool:
    text = normalize_text(hit_text(hit))
    if normalize_text(expected_title) and normalize_text(expected_title) in text:
        return True
    return any(normalize_text(keyword) in text for keyword in expected_keywords)


def calculate_hit_at_k(hits: list[dict[str, Any]], expected_title: str, expected_keywords: list[str], k: int) -> int:
    return 1 if any(is_expected_hit(hit, expected_title, expected_keywords) for hit in hits[:k]) else 0


def calculate_reciprocal_rank(hits: list[dict[str, Any]], expected_title: str, expected_keywords: list[str]) -> float:
    for index, hit in enumerate(hits, start=1):
        if is_expected_hit(hit, expected_title, expected_keywords):
            return round(1 / index, 4)
    return 0.0


def calculate_keyword_coverage(hits: list[dict[str, Any]], expected_keywords: list[str], k: int) -> float:
    if not expected_keywords:
        return 0.0
    text = normalize_text(" ".join(hit_text(hit) for hit in hits[:k]))
    matched = sum(1 for keyword in expected_keywords if normalize_text(keyword) in text)
    return round(matched / len(expected_keywords), 4)
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_evaluation.py -q
```

Expected: metric tests pass.

## Task 3: Evaluate Single Case and Summarize Mode

**Files:**
- Modify: `backend_python/rag_evaluation.py`
- Modify: `tests/test_rag_evaluation.py`

- [ ] Write failing tests for case evaluation and summary.

```python
from backend_python.rag_evaluation import evaluate_case, summarize_mode_results


def test_evaluate_case_returns_metrics_and_top_titles() -> None:
    case = {
        "id": "rag_log_fields",
        "query": "RAG 日志字段",
        "knowledgeBase": "role_knowledge",
        "expectedTitle": "RAG 日志工程化",
        "expectedKeywords": ["query_text", "hit_count"],
    }
    hits = [
        {"title": "RAG 日志工程化", "content": "query_text"},
        {"title": "其它", "content": "hit_count"},
    ]

    result = evaluate_case(case, hits, k=2)

    assert result["caseId"] == "rag_log_fields"
    assert result["hitAtK"] == 1
    assert result["reciprocalRank"] == 1.0
    assert result["keywordCoverage"] == 1.0
    assert result["topTitles"] == ["RAG 日志工程化", "其它"]


def test_summarize_mode_results_averages_metrics() -> None:
    summary = summarize_mode_results(
        [
            {"hitAtK": 1, "reciprocalRank": 1.0, "keywordCoverage": 0.5},
            {"hitAtK": 0, "reciprocalRank": 0.0, "keywordCoverage": 0.25},
        ]
    )

    assert summary == {
        "caseCount": 2,
        "hitAtK": 0.5,
        "mrr": 0.5,
        "keywordCoverage": 0.375,
    }
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_evaluation.py::test_evaluate_case_returns_metrics_and_top_titles tests/test_rag_evaluation.py::test_summarize_mode_results_averages_metrics -q
```

Expected: missing `evaluate_case` or `summarize_mode_results`.

- [ ] Implement evaluation and summary.

```python
def evaluate_case(case: dict[str, Any], hits: list[dict[str, Any]], k: int) -> dict[str, Any]:
    expected_title = str(case.get("expectedTitle") or "")
    expected_keywords = [str(item) for item in case.get("expectedKeywords") or []]
    top_hits = hits[:k]
    return {
        "caseId": case.get("id"),
        "query": case.get("query"),
        "knowledgeBase": case.get("knowledgeBase"),
        "hitAtK": calculate_hit_at_k(hits, expected_title, expected_keywords, k),
        "reciprocalRank": calculate_reciprocal_rank(hits, expected_title, expected_keywords),
        "keywordCoverage": calculate_keyword_coverage(hits, expected_keywords, k),
        "topTitles": [str(hit.get("title") or "") for hit in top_hits],
    }


def summarize_mode_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"caseCount": 0, "hitAtK": 0.0, "mrr": 0.0, "keywordCoverage": 0.0}
    count = len(results)
    return {
        "caseCount": count,
        "hitAtK": round(sum(float(item["hitAtK"]) for item in results) / count, 4),
        "mrr": round(sum(float(item["reciprocalRank"]) for item in results) / count, 4),
        "keywordCoverage": round(sum(float(item["keywordCoverage"]) for item in results) / count, 4),
    }
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_evaluation.py -q
```

Expected: all RAG evaluation unit tests pass.

## Task 4: Evaluation Runner Function

**Files:**
- Modify: `backend_python/rag_evaluation.py`
- Add: `tests/test_rag_evaluation_script.py`

- [ ] Write failing test for evaluating modes with injected retriever.

```python
from backend_python.rag_evaluation import evaluate_modes


def test_evaluate_modes_runs_each_mode_and_isolates_failures() -> None:
    cases = [
        {
            "id": "case_1",
            "query": "RAG 日志字段",
            "knowledgeBase": "role_knowledge",
            "expectedTitle": "RAG 日志工程化",
            "expectedKeywords": ["query_text"],
        }
    ]

    def fake_retriever(case: dict, mode: str, k: int) -> list[dict]:
        if mode == "vector":
            raise RuntimeError("embedding failed")
        return [{"title": "RAG 日志工程化", "content": "query_text"}]

    result = evaluate_modes(cases, modes=["bm25", "vector"], k=3, retriever=fake_retriever)

    assert result["k"] == 3
    assert result["modes"]["bm25"]["summary"]["hitAtK"] == 1.0
    assert result["modes"]["vector"]["summary"]["caseCount"] == 0
    assert result["modes"]["vector"]["errors"][0]["caseId"] == "case_1"
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_evaluation_script.py::test_evaluate_modes_runs_each_mode_and_isolates_failures -q
```

Expected: missing `evaluate_modes`.

- [ ] Implement `evaluate_modes`.

```python
from collections.abc import Callable


Retriever = Callable[[dict[str, Any], str, int], list[dict[str, Any]]]


def evaluate_modes(
    cases: list[dict[str, Any]],
    *,
    modes: list[str],
    k: int,
    retriever: Retriever,
) -> dict[str, Any]:
    output: dict[str, Any] = {"k": k, "modes": {}}
    for mode in modes:
        case_results = []
        errors = []
        for case in cases:
            try:
                hits = retriever(case, mode, k)
                case_results.append(evaluate_case(case, hits, k))
            except Exception as exc:
                errors.append({"caseId": case.get("id"), "error": str(exc)})
        output["modes"][mode] = {
            "summary": summarize_mode_results(case_results),
            "cases": case_results,
            "errors": errors,
        }
    return output
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_evaluation.py tests/test_rag_evaluation_script.py -q
```

Expected: evaluation module and runner function tests pass.

## Task 5: Command Line Script

**Files:**
- Add: `scripts/run_rag_evaluation.py`
- Modify: `tests/test_rag_evaluation_script.py`

- [ ] Write failing test for script-level JSON output using a fake runner.

```python
import json

from scripts.run_rag_evaluation import render_result


def test_render_result_outputs_pretty_json() -> None:
    rendered = render_result({"k": 3, "modes": {"bm25": {"summary": {"hitAtK": 1.0}}}})

    data = json.loads(rendered)
    assert data["k"] == 3
    assert data["modes"]["bm25"]["summary"]["hitAtK"] == 1.0
    assert "\n" in rendered
```

- [ ] Verify RED.

```powershell
python -m pytest tests/test_rag_evaluation_script.py::test_render_result_outputs_pretty_json -q
```

Expected: missing script.

- [ ] Implement command line script.

```python
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend_python.database import SessionLocal, init_db
from backend_python.rag_evaluation import evaluate_modes
from backend_python.retrieval_service import retrieve_chunks

CASE_PATH = ROOT_DIR / "data" / "rag_evaluation_cases.json"
DEFAULT_MODES = ["bm25", "vector", "hybrid", "hybrid_rerank"]


def load_cases(path: Path = CASE_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_result(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    init_db()
    cases = load_cases()
    with SessionLocal() as db:
        user_id = 1

        def retriever(case: dict, mode: str, k: int) -> list[dict]:
            return retrieve_chunks(
                db,
                user_id=user_id,
                knowledge_base=case["knowledgeBase"],
                query=case["query"],
                limit=k,
                mode=mode,
            )

        result = evaluate_modes(cases, modes=DEFAULT_MODES, k=3, retriever=retriever)
    print(render_result(result))


if __name__ == "__main__":
    main()
```

- [ ] Verify GREEN.

```powershell
python -m pytest tests/test_rag_evaluation_script.py -q
```

Expected: script unit tests pass.

## Task 6: Verification

- [ ] Run focused tests.

```powershell
python -m pytest tests/test_rag_evaluation.py tests/test_rag_evaluation_script.py tests/test_rag_rerank_retrieval.py tests/test_rag_hybrid_retrieval.py -q
```

Expected: focused tests pass.

- [ ] Run script smoke test.

```powershell
python scripts/run_rag_evaluation.py
```

Expected: prints valid JSON. Some modes may contain errors if local data/API key is not prepared.

- [ ] Run full backend tests.

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] Run frontend smoke checks.

```powershell
node tests/frontend_rag_documents.test.mjs
node tests/frontend_rag_logs.test.mjs
node --check app.js
```

Expected: each command exits with code 0.

## Self-Review

- Spec coverage: 评估集、Hit@K、MRR、关键词覆盖率、模式汇总、脚本输出、失败隔离均已覆盖。
- Scope check: V1 不做前端、不建表、不使用大模型裁判。
- Type consistency: case 字段使用 `expectedTitle`、`expectedKeywords`；模式使用 `bm25`、`vector`、`hybrid`、`hybrid_rerank`。
- Testing discipline: 每个行为都先写失败测试，再写最小实现。

