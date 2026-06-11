from collections.abc import Callable
from typing import Any

from .rag_metadata import metadata_matches, normalize_rag_hit_metadata

Retriever = Callable[[dict[str, Any], str, int], list[dict[str, Any]]]


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


def normalize_keyword_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def normalize_evaluation_case(case: dict[str, Any]) -> dict[str, Any]:
    knowledge_base = str(case.get("knowledgeBase") or "")
    return {
        **case,
        "id": str(case.get("id") or ""),
        "query": str(case.get("query") or ""),
        "knowledgeBase": knowledge_base,
        "expectedTitle": str(case.get("expectedTitle") or ""),
        "expectedKeywords": normalize_keyword_list(case.get("expectedKeywords")),
        "expectedKnowledgeBase": str(case.get("expectedKnowledgeBase") or knowledge_base),
        "expectedPositionTag": str(case.get("expectedPositionTag") or ""),
        "expectedStage": str(case.get("expectedStage") or ""),
    }


def filter_evaluation_cases(
    cases: list[dict[str, Any]],
    *,
    knowledge_base: str = "",
    position_tag: str = "",
) -> list[dict[str, Any]]:
    normalized_cases = [normalize_evaluation_case(case) for case in cases]
    output = []
    for case in normalized_cases:
        if knowledge_base and case.get("knowledgeBase") != knowledge_base:
            continue
        if position_tag and case.get("expectedPositionTag") != position_tag:
            continue
        output.append(case)
    return output


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


def evaluate_case(case: dict[str, Any], hits: list[dict[str, Any]], k: int) -> dict[str, Any]:
    expected_title = str(case.get("expectedTitle") or "")
    expected_keywords = [str(item) for item in case.get("expectedKeywords") or []]
    top_hits = hits[:k]
    expected_knowledge_base = str(case.get("expectedKnowledgeBase") or case.get("knowledgeBase") or "")
    expected_position_tag = str(case.get("expectedPositionTag") or "")
    expected_stage = str(case.get("expectedStage") or "")
    metadata_match = any(
        metadata_matches(
            normalize_rag_hit_metadata(hit, retriever_name=str(case.get("knowledgeBase") or "")),
            expected_knowledge_base=expected_knowledge_base,
            expected_position_tag=expected_position_tag,
            expected_stage=expected_stage,
        )
        for hit in top_hits
    )
    return {
        "caseId": case.get("id"),
        "query": case.get("query"),
        "knowledgeBase": case.get("knowledgeBase"),
        "hitAtK": calculate_hit_at_k(hits, expected_title, expected_keywords, k),
        "reciprocalRank": calculate_reciprocal_rank(hits, expected_title, expected_keywords),
        "keywordCoverage": calculate_keyword_coverage(hits, expected_keywords, k),
        "metadataMatch": 1 if metadata_match else 0,
        "emptyRecall": 0 if hits else 1,
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
        "metadataMatchRate": round(sum(float(item.get("metadataMatch") or 0) for item in results) / count, 4),
        "emptyRecallRate": round(sum(float(item.get("emptyRecall") or 0) for item in results) / count, 4),
    }


def classify_case_result(result: dict[str, Any], *, keyword_threshold: float = 0.5) -> str:
    if int(result.get("emptyRecall") or 0) == 1:
        return "empty_recall"
    if int(result.get("metadataMatch") or 0) == 0:
        return "metadata_miss"
    if int(result.get("hitAtK") or 0) == 0:
        return "missed_expected_hit"
    if float(result.get("keywordCoverage") or 0.0) < keyword_threshold:
        return "weak_keyword_coverage"
    return "ok"


def build_failure_analysis(
    results: list[dict[str, Any]],
    *,
    keyword_threshold: float = 0.5,
    sample_limit: int = 8,
) -> dict[str, Any]:
    reasons = ["empty_recall", "metadata_miss", "missed_expected_hit", "weak_keyword_coverage"]
    by_reason: dict[str, dict[str, Any]] = {
        reason: {"count": 0, "caseIds": []}
        for reason in reasons
    }
    total_failure_count = 0
    for result in results:
        reason = classify_case_result(result, keyword_threshold=keyword_threshold)
        if reason == "ok":
            continue
        total_failure_count += 1
        bucket = by_reason[reason]
        bucket["count"] += 1
        if len(bucket["caseIds"]) < sample_limit:
            bucket["caseIds"].append(result.get("caseId"))
    return {
        "totalFailureCount": total_failure_count,
        "byReason": by_reason,
    }


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
            "failureAnalysis": build_failure_analysis(case_results),
            "cases": case_results,
            "errors": errors,
        }
    return output


def run_evaluation_suite(
    cases: list[dict[str, Any]],
    *,
    modes: list[str],
    k: int,
    retriever: Retriever,
) -> dict[str, Any]:
    normalized_cases = [normalize_evaluation_case(case) for case in cases]
    report = evaluate_modes(normalized_cases, modes=modes, k=k, retriever=retriever)
    report["caseCount"] = len(normalized_cases)
    report["metricDefinitions"] = explain_evaluation_metrics()
    for mode_result in report["modes"].values():
        mode_result["caseInsights"] = [build_case_insight(result) for result in mode_result.get("cases", [])]
    return report
