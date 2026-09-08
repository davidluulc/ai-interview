"""Stage 3 RRF fusion experiment: bm25 / vector / hybrid-weighted / hybrid-rrf.

同步脚本（检索入口是同步的）。流程：

1. 连本地库（database.py SessionLocal；user=1 无 evaluation_seed 数据则先 seed）。
2. 对 data/rag_evaluation_cases.json 的每个用例 x 四种模式取 hits（k=3，与现有评测口径一致）：
   bm25 / vector / hybrid-weighted / hybrid-rrf。
3. 逐 case evaluate_case，按模式 summarize_mode_results，并测量每模式总 wall time。
4. 打印 Markdown 结果表 + 结论模板到 stdout，并写入
   .superpowers/sdd/agent-v3-upgrade-stage3-rrf/experiment-output.md（scratch，Task 4 的原料）。

向量侧说明：
- 默认走真实 embed_text。本地无 DASHSCOPE/zhipu key 时 query embedding 失败，
  vector/hybrid 的向量一路为空——脚本检测后打印警告并继续（数字如实记录）。
  此时 weighted/rrf 都退化为 bm25 单路排序（见输出中的退化说明）。
- --mock-vector 复用 scripts/run_rag_evaluation.py 的确定性静态向量方案
  （每个 case 映射到固定 3 维向量，seed 语料模型标记为 evaluation-static），
  使四组数字在本地完整可评。两种跑法都会如实标注在输出里。
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import func, select

from backend_python.config import DATABASE_URL, HYBRID_FUSION_MODE, VECTOR_SEARCH_BACKEND
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import RagChunk
from backend_python.rag_evaluation import (
    evaluate_case,
    normalize_evaluation_case,
    summarize_mode_results,
)
from backend_python.rag_evaluation_seed import (
    EVALUATION_SEED_DOCUMENTS,
    EVALUATION_SEED_SOURCE,
    seed_evaluation_documents,
)
from backend_python import retrieval_service
from backend_python.retrieval_service import retrieve_chunks, retrieve_hybrid_chunks, run_query_embedding
from scripts.run_rag_evaluation import MOCK_QUERY_EMBEDDINGS

CASE_PATH = ROOT_DIR / "data" / "rag_evaluation_cases.json"
OUTPUT_PATH = ROOT_DIR / ".superpowers" / "sdd" / "agent-v3-upgrade-stage3-rrf" / "experiment-output.md"
USER_ID = 1
K = 3
VECTOR_UNAVAILABLE_WARNING = (
    "向量组在本地无 embedding 数据，向量/hybrid 组数字不完整，"
    "结论标注局限，公网 pgvector 环境复跑"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG fusion (weighted vs rrf) experiment.")
    parser.add_argument(
        "--mock-vector",
        action="store_true",
        help="用 run_rag_evaluation.py 的确定性静态向量代替真实 embed_text（本地无 key 时四组完整可评）。",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="把本次结果追加到 experiment-output.md 而不是覆盖（默认覆盖）。",
    )
    return parser.parse_args(argv)


def load_cases(path: Path = CASE_PATH) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    return [normalize_evaluation_case(case) for case in cases]


def install_mock_vector_clients(case: dict[str, Any]) -> None:
    """复用 run_rag_evaluation.py 的 mock 方案；仅运行期替换，不改生产代码。

    seed 语料的 embedding_model 是 "evaluation-static"（见 rag_evaluation_seed.py），
    向量检索按 current_embedding_model() 过滤，因此 mock 时必须同时替换两者，
    向量一路才会命中 seed 语料。
    """
    from scripts.run_rag_evaluation import build_mock_query_embedding

    async def fake_embed_text(text: str) -> list[float]:
        return build_mock_query_embedding(case)

    retrieval_service.embed_text = fake_embed_text
    retrieval_service.current_embedding_model = lambda: "evaluation-static"


def probe_query_embedding() -> tuple[bool, str]:
    try:
        embedding = run_query_embedding("embedding 可用性探测")
    except Exception as exc:  # noqa: BLE001 - 任何失败都表示向量侧不可用，需如实记录
        return False, str(exc)
    if not embedding:
        return False, "query embedding 返回空向量"
    return True, "ok"


def count_chunks(db: Any, *conditions: Any) -> int:
    return int(db.scalar(select(func.count()).select_from(RagChunk).where(*conditions)) or 0)


def ensure_corpus(db: Any) -> dict[str, int]:
    """user=1 视角下没有 evaluation_seed 语料时先 seed（seed 函数幂等：先删后建）。"""

    owned = count_chunks(db, RagChunk.user_id == USER_ID)
    eval_seed_chunks = count_chunks(
        db,
        RagChunk.user_id == USER_ID,
        RagChunk.metadata_json.like(f'%"{EVALUATION_SEED_SOURCE}"%'),
    )
    seeded = 0
    if eval_seed_chunks == 0:
        seeded = seed_evaluation_documents(db, user_id=USER_ID)
        eval_seed_chunks = count_chunks(
            db,
            RagChunk.user_id == USER_ID,
            RagChunk.metadata_json.like(f'%"{EVALUATION_SEED_SOURCE}"%'),
        )
    ready = count_chunks(
        db,
        RagChunk.user_id == USER_ID,
        RagChunk.embedding_status == "ready",
    )
    return {
        "ownedChunks": owned if not seeded else count_chunks(db, RagChunk.user_id == USER_ID),
        "seededDocuments": seeded,
        "evalSeedChunks": eval_seed_chunks,
        "readyEmbeddingChunks": ready,
    }


def fetch_hits(db: Any, case: dict[str, Any], mode: str, *, mock_vector: bool) -> list[dict[str, Any]]:
    if mock_vector:
        install_mock_vector_clients(case)
    if mode == "bm25":
        return retrieve_chunks(
            db, user_id=USER_ID, knowledge_base=case["knowledgeBase"], query=case["query"], limit=K, mode="bm25"
        )
    if mode == "vector":
        return retrieve_chunks(
            db, user_id=USER_ID, knowledge_base=case["knowledgeBase"], query=case["query"], limit=K, mode="vector"
        )
    if mode == "hybrid-weighted":
        return retrieve_hybrid_chunks(
            db,
            user_id=USER_ID,
            knowledge_base=case["knowledgeBase"],
            query=case["query"],
            limit=K,
            fusion="weighted",
        )
    if mode == "hybrid-rrf":
        return retrieve_hybrid_chunks(
            db,
            user_id=USER_ID,
            knowledge_base=case["knowledgeBase"],
            query=case["query"],
            limit=K,
            fusion="rrf",
        )
    raise ValueError(f"unknown mode: {mode}")


def run_mode(db: Any, cases: list[dict[str, Any]], mode: str, *, mock_vector: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    started = time.perf_counter()
    for case in cases:
        try:
            hits = fetch_hits(db, case, mode, mock_vector=mock_vector)
            results.append(evaluate_case(case, hits, K))
        except Exception as exc:  # noqa: BLE001 - 单 case 失败不中断实验，如实记录
            errors.append(f"{case.get('id')}: {exc}")
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    summary = summarize_mode_results(results)
    return {
        "summary": summary,
        "elapsedMs": elapsed_ms,
        "errors": errors,
        "results": results,
    }


def format_metric(value: Any) -> str:
    return f"{float(value):.4f}"


def count_mock_vector_coverage(cases: list[dict[str, Any]]) -> dict[str, int]:
    """统计 mock 静态向量方案在当前用例集上的覆盖（动态计算，避免模板里硬编码数字漂移）。"""

    default_embedding = [1.0, 0.0, 0.0]
    case_ids = [str(case.get("id") or "") for case in cases]
    explicit_ids = {case_id for case_id in case_ids if case_id in MOCK_QUERY_EMBEDDINGS}
    default_count = len(case_ids) - len(explicit_ids)
    explicit_same_as_default = sum(
        1 for case_id in explicit_ids if MOCK_QUERY_EMBEDDINGS[case_id] == default_embedding
    )
    return {
        "total": len(case_ids),
        "explicit": len(explicit_ids),
        "default": default_count,
        "explicitSameAsDefault": explicit_same_as_default,
        "effectiveDefaultVector": default_count + explicit_same_as_default,
    }


def render_report(
    *,
    args: argparse.Namespace,
    cases: list[dict[str, Any]],
    corpus: dict[str, int],
    embedding_available: bool,
    embedding_reason: str,
    mode_runs: dict[str, dict[str, Any]],
) -> str:
    vector_side = "mock 静态向量（--mock-vector，复用 run_rag_evaluation.py 的 case→固定 3 维向量映射）" if args.mock_vector else "真实 embed_text（本地 .env 未配置 key 时为空召回）"
    dialect = DATABASE_URL.split(":", 1)[0]
    lines: list[str] = []
    lines.append("# RAG Fusion 实验原始输出（weighted vs rrf，Stage 3 Task 3）")
    lines.append("")
    lines.append(f"- 运行时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 向量侧：{vector_side}")
    lines.append(f"- 数据库：{dialect}（VECTOR_SEARCH_BACKEND={VECTOR_SEARCH_BACKEND}，HYBRID_FUSION_MODE 默认={HYBRID_FUSION_MODE}）")
    lines.append(
        "- 语料：user=1 evaluation_seed chunks={evalSeedChunks}（ready embedding={readyEmbeddingChunks}，"
        "seed 文档数={seededDocuments}，期望 {expectedDocs}）；user=1 全部 chunks={ownedChunks}".format(
            expectedDocs=len(EVALUATION_SEED_DOCUMENTS), **corpus
        )
    )
    if corpus["seededDocuments"]:
        lines.append("  - 本次运行执行了 seed_evaluation_documents（本地无 user=1 语料，先 seed 再跑）")
    lines.append(f"- 用例：{CASE_PATH.name}，共 {len(cases)} 例；k=3，limit=3，与现有评测口径一致")
    lines.append("")

    if not embedding_available and not args.mock_vector:
        lines.append(f"> [警告] {VECTOR_UNAVAILABLE_WARNING}")
        lines.append(f"> 检测详情：{embedding_reason}")
        lines.append("")

    lines.append("## 结果表")
    lines.append("")
    lines.append("| 模式 | caseCount | hit@3 | MRR | keywordCoverage | 耗时(ms) |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for mode in ("bm25", "vector", "hybrid-weighted", "hybrid-rrf"):
        run = mode_runs[mode]
        summary = run["summary"]
        lines.append(
            "| {mode} | {caseCount} | {hit} | {mrr} | {kw} | {elapsed} |".format(
                mode=mode,
                caseCount=summary["caseCount"],
                hit=format_metric(summary["hitAtK"]),
                mrr=format_metric(summary["mrr"]),
                kw=format_metric(summary["keywordCoverage"]),
                elapsed=run["elapsedMs"],
            )
        )
    lines.append("")
    total_case_ms = {
        mode: round(run["elapsedMs"] / max(run["summary"]["caseCount"], 1), 2) for mode, run in mode_runs.items()
    }
    lines.append(
        "每 case 平均耗时(ms)：" + "，".join(f"{mode}={value}" for mode, value in total_case_ms.items()) + "。"
    )
    for mode in ("bm25", "vector", "hybrid-weighted", "hybrid-rrf"):
        if mode_runs[mode]["errors"]:
            sample = mode_runs[mode]["errors"][:3]
            lines.append(f"- {mode} 有 {len(mode_runs[mode]['errors'])} 个 case 报错（样例：{sample}）")

    weighted_results = mode_runs["hybrid-weighted"]["results"]
    rrf_results = mode_runs["hybrid-rrf"]["results"]
    same_order = sum(
        1
        for left, right in zip(weighted_results, rrf_results, strict=False)
        if list(left.get("topTitles") or []) == list(right.get("topTitles") or [])
    )
    compared = min(len(weighted_results), len(rrf_results))
    lines.append(f"- weighted 与 rrf 的 top3 顺序完全一致的 case 数：{same_order}/{compared}")
    lines.append("")

    lines.append("## 结论（模板，数字均为本次真实跑数）")
    lines.append("")
    best_hit = max(mode_runs, key=lambda mode: mode_runs[mode]["summary"]["hitAtK"])
    best_mrr = max(mode_runs, key=lambda mode: mode_runs[mode]["summary"]["mrr"])
    lines.append(f"- 胜者（hit@3）：{best_hit}（{format_metric(mode_runs[best_hit]['summary']['hitAtK'])}）")
    lines.append(f"- 胜者（MRR）：{best_mrr}（{format_metric(mode_runs[best_mrr]['summary']['mrr'])}）")
    weighted_summary = mode_runs["hybrid-weighted"]["summary"]
    rrf_summary = mode_runs["hybrid-rrf"]["summary"]
    lines.append(
        f"- weighted vs rrf 差距：hit@3 {format_metric(weighted_summary['hitAtK'])} vs "
        f"{format_metric(rrf_summary['hitAtK'])}；MRR {format_metric(weighted_summary['mrr'])} vs "
        f"{format_metric(rrf_summary['mrr'])}"
    )
    if not embedding_available and not args.mock_vector:
        lines.append(
            "- 局限（向量组完整性）：本地无可用 embedding 服务，vector 组 0 召回；hybrid 两组的向量一路为空，"
            "weighted 与 rrf 都退化为 bm25 单路排序（两者分别是 bm25 分数的单调归一化与名次的单调函数，"
            "顺序必然与 bm25 一致），因此 weighted/rrf 数字并列不构成融合策略差异的证据，"
            "仅验证两条融合代码路径在空向量侧下行为一致、不崩溃。"
            "融合策略差异需在 --mock-vector 跑法或公网 pgvector（真实 2048 维向量）环境复跑后再下结论。"
        )
    if args.mock_vector:
        coverage = count_mock_vector_coverage(cases)
        lines.append(
            "- 局限（mock 向量）：--mock-vector 使用 run_rag_evaluation.py 的确定性静态 3 维向量（case→固定向量，"
            f"其中 {coverage['explicit']}/{coverage['total']} 例有显式映射、其余 {coverage['default']} 例默认 [1,0,0]，"
            f"另有 {coverage['explicitSameAsDefault']} 个显式映射亦为 [1,0,0]，"
            f"共 {coverage['effectiveDefaultVector']} 例实际查询同一向量），与真实语义 embedding 行为不可比；"
            "该跑法仅用于让四组在本地完整可评、观察两路都有召回时 weighted 与 rrf 的排序差异。"
        )
    lines.append(
        "- 局限（口径）：case 数 38、seed 语料为人工构造、无生产流量分布；"
        "耗时为本地 SQLite 单进程 wall time（含 mock 时的进程内向量计算），仅做相对比较。"
    )
    lines.append("")
    return "\n".join(lines)


def write_output(text: str, *, append: bool) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if append:
        with OUTPUT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    else:
        OUTPUT_PATH.write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    init_db()
    cases = load_cases()
    embedding_available, embedding_reason = probe_query_embedding()
    with SessionLocal() as db:
        corpus = ensure_corpus(db)
        mode_runs = {
            mode: run_mode(db, cases, mode, mock_vector=args.mock_vector)
            for mode in ("bm25", "vector", "hybrid-weighted", "hybrid-rrf")
        }
    report = render_report(
        args=args,
        cases=cases,
        corpus=corpus,
        embedding_available=embedding_available,
        embedding_reason=embedding_reason,
        mode_runs=mode_runs,
    )
    print(report)
    write_output(report, append=args.append)
    print(f"[experiment] 原始输出已写入：{OUTPUT_PATH}（{'append' if args.append else 'overwrite'}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
