from typing import Any


def hit_score(hit: dict[str, Any]) -> float:
    try:
        return float(hit.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def is_database_hit(hit: dict[str, Any]) -> bool:
    return hit.get("source") == "database" or bool(hit.get("chunkId"))


def summarize_retrieval_sources(hits: list[dict[str, Any]]) -> dict[str, Any]:
    database_hit_count = sum(1 for hit in hits if is_database_hit(hit))
    seed_hit_count = max(len(hits) - database_hit_count, 0)
    return {
        "databaseHitCount": database_hit_count,
        "seedHitCount": seed_hit_count,
        "hasDatabaseHits": database_hit_count > 0,
        "hasSeedFallback": seed_hit_count > 0,
    }


def evaluate_retrieval_quality(hits: list[dict[str, Any]]) -> dict[str, Any]:
    if not hits:
        return {
            "level": "miss",
            "label": "未命中",
            "hitCount": 0,
            "maxScore": 0,
            "averageScore": 0,
            "databaseHitCount": 0,
            "seedHitCount": 0,
            "reason": "没有召回任何资料，模型只能依赖用户输入和通用能力。",
        }

    scores = [hit_score(hit) for hit in hits]
    max_score = round(max(scores), 2)
    average_score = round(sum(scores) / len(scores), 2)
    source_summary = summarize_retrieval_sources(hits)

    if (len(hits) >= 2 and max_score >= 6 and average_score >= 4) or max_score >= 8:
        level = "good"
        label = "命中良好"
        reason = "召回结果相关性较高，可以作为 prompt 上下文使用。"
    else:
        level = "weak"
        label = "命中偏弱"
        reason = "有召回资料，但命中数量或分数偏低，需要补充知识库或优化 query。"

    return {
        "level": level,
        "label": label,
        "hitCount": len(hits),
        "maxScore": max_score,
        "averageScore": average_score,
        "databaseHitCount": source_summary["databaseHitCount"],
        "seedHitCount": source_summary["seedHitCount"],
        "reason": reason,
    }
