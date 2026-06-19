import math
import re
import asyncio
from collections import Counter
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .db_models import RagChunk, RagDocument
from .embedding_client import current_embedding_model, embed_text
from .query_rewrite import build_query_variants
from .rag_store import VALID_KNOWLEDGE_BASES, chunk_matches_metadata_filter, normalize_metadata_filter, parse_json
from .rerank_client import rerank_documents
from .vector_store import SQLiteVectorStore


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", str(text or "").lower())
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        if token not in seen:
            result.append(token)
            seen.add(token)
    return result


def chunk_text(chunk: RagChunk) -> str:
    keywords = " ".join(str(item) for item in parse_json(chunk.keywords_json, []))
    metadata = " ".join(str(value) for value in parse_json(chunk.metadata_json, {}).values())
    return f"{chunk.title} {chunk.content} {keywords} {metadata}"


def bm25_score(
    query_tokens: list[str],
    document_tokens: list[str],
    corpus_tokens: list[list[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    if not query_tokens or not document_tokens or not corpus_tokens:
        return 0.0

    term_frequency = Counter(document_tokens)
    document_count = len(corpus_tokens)
    average_length = sum(len(tokens) for tokens in corpus_tokens) / max(document_count, 1)
    document_length = len(document_tokens)
    score = 0.0

    for token in query_tokens:
        frequency = term_frequency[token]
        if frequency <= 0:
            continue
        document_frequency = sum(1 for tokens in corpus_tokens if token in tokens)
        idf = math.log(1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5))
        denominator = frequency + k1 * (1 - b + b * document_length / max(average_length, 1))
        score += idf * ((frequency * (k1 + 1)) / denominator)

    return round(score, 4)


def matched_tokens(query_tokens: list[str], document_tokens: list[str]) -> list[str]:
    document_token_set = set(document_tokens)
    return [token for token in query_tokens if token in document_token_set][:8]


def visible_enabled_chunk_filters(user_id: int, knowledge_base: str) -> tuple[Any, ...]:
    return (
        RagChunk.knowledge_base == knowledge_base,
        RagDocument.status == "enabled",
        or_(RagDocument.user_id == user_id, RagDocument.visibility == "public"),
    )


def document_lifecycle_fields(chunk: RagChunk) -> dict[str, str]:
    document = chunk.document
    return {
        "documentStatus": getattr(document, "status", None) or "enabled",
        "documentVisibility": getattr(document, "visibility", None) or "private",
    }


def filter_chunks_by_metadata(chunks: list[RagChunk], metadata_filter: dict[str, Any] | None) -> list[RagChunk]:
    normalized_filter = normalize_metadata_filter(metadata_filter)
    if not normalized_filter:
        return chunks
    return [
        chunk
        for chunk in chunks
        if chunk_matches_metadata_filter(parse_json(chunk.metadata_json, {}), normalized_filter)
    ]


def metadata_filter_hit_fields(metadata_filter: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "metadataFilter": normalize_metadata_filter(metadata_filter),
        "metadataMatch": True,
    }


def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    if all(score <= 0 for score in scores):
        return [0.0 for _ in scores]
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0 if score > 0 else 0.0 for score in scores]
    return [round((score - min_score) / (max_score - min_score), 4) for score in scores]


def normalize_hybrid_weights(weights: dict[str, Any] | None = None) -> dict[str, float]:
    if not isinstance(weights, dict):
        return {"bm25": 0.6, "vector": 0.4}
    try:
        bm25_weight = max(float(weights.get("bm25", 0.6)), 0.0)
        vector_weight = max(float(weights.get("vector", 0.4)), 0.0)
    except (TypeError, ValueError):
        return {"bm25": 0.6, "vector": 0.4}
    total = bm25_weight + vector_weight
    if total <= 0:
        return {"bm25": 0.6, "vector": 0.4}
    return {
        "bm25": round(bm25_weight / total, 4),
        "vector": round(vector_weight / total, 4),
    }


def merge_hybrid_hits(
    bm25_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    *,
    limit: int,
    bm25_weight: float = 0.6,
    vector_weight: float = 0.4,
) -> list[dict[str, Any]]:
    weights = normalize_hybrid_weights({"bm25": bm25_weight, "vector": vector_weight})
    bm25_normalized = normalize_scores([float(hit.get("score") or 0) for hit in bm25_hits])
    vector_normalized = normalize_scores([float(hit.get("score") or 0) for hit in vector_hits])
    merged: dict[int, dict[str, Any]] = {}

    def ensure_item(hit: dict[str, Any]) -> dict[str, Any]:
        chunk_id = int(hit.get("chunkId") or 0)
        if chunk_id not in merged:
            merged[chunk_id] = {
                **hit,
                "retrievalMode": "hybrid",
                "matchedRetrievalModes": [],
                "bm25Score": 0.0,
                "vectorScore": 0.0,
                "hybridScore": 0.0,
                "hybridWeights": weights,
            }
        return merged[chunk_id]

    for hit, normalized_score in zip(bm25_hits, bm25_normalized, strict=False):
        item = ensure_item(hit)
        item["bm25Score"] = hit.get("score") or 0.0
        item["hybridScore"] += weights["bm25"] * normalized_score
        if "bm25" not in item["matchedRetrievalModes"]:
            item["matchedRetrievalModes"].append("bm25")

    for hit, normalized_score in zip(vector_hits, vector_normalized, strict=False):
        item = ensure_item(hit)
        item["vectorScore"] = hit.get("score") or 0.0
        item["hybridScore"] += weights["vector"] * normalized_score
        if "vector" not in item["matchedRetrievalModes"]:
            item["matchedRetrievalModes"].append("vector")

    results = []
    for item in merged.values():
        item["hybridScore"] = round(float(item["hybridScore"]), 4)
        item["score"] = item["hybridScore"]
        results.append(item)
    results.sort(key=lambda item: item["hybridScore"], reverse=True)
    return results[:limit]


def retrieve_multi_query_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    profile: dict[str, Any] | None = None,
    stage: str = "",
    weakness_tags: list[str] | None = None,
    limit: int = 3,
    mode: str = "bm25",
    metadata_filter: dict[str, Any] | None = None,
    hybrid_weights: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    query_variants = build_query_variants(
        query,
        profile=profile,
        stage=stage,
        weakness_tags=weakness_tags,
    )
    if not query_variants:
        return []

    merged: dict[int, dict[str, Any]] = {}
    recall_limit = max(limit * 2, 6)
    for variant in query_variants:
        hits = retrieve_chunks(
            db,
            user_id=user_id,
            knowledge_base=knowledge_base,
            query=variant["query"],
            limit=recall_limit,
            mode=mode,
            metadata_filter=metadata_filter,
            hybrid_weights=hybrid_weights,
        )
        for hit in hits:
            chunk_id = int(hit.get("chunkId") or 0)
            if chunk_id <= 0:
                continue
            enriched_hit = {
                **hit,
                "matchedQueryVariant": variant["name"],
                "queryVariants": query_variants,
            }
            previous = merged.get(chunk_id)
            if previous is None or float(enriched_hit.get("score") or 0) > float(previous.get("score") or 0):
                merged[chunk_id] = enriched_hit

    results = list(merged.values())
    results.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return results[:limit]


def hit_to_rerank_document(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata") or {}
    metadata_text = " ".join(str(value) for value in metadata.values())
    return "\n".join(
        [
            f"标题：{hit.get('title') or ''}",
            f"内容：{hit.get('content') or ''}",
            f"元数据：{metadata_text}",
        ]
    ).strip()


def apply_rerank_results(
    hits: list[dict[str, Any]],
    rerank_results: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    reranked = []
    for result in rerank_results:
        index = int(result["index"])
        if index < 0 or index >= len(hits):
            continue
        item = {**hits[index]}
        modes = list(item.get("matchedRetrievalModes") or [])
        if "rerank" not in modes:
            modes.append("rerank")
        item["retrievalMode"] = "hybrid_rerank"
        item["matchedRetrievalModes"] = modes
        item["rerankScore"] = float(result["relevance_score"])
        item["rerankIndex"] = index
        item["preRerankRank"] = index + 1
        item["score"] = item["rerankScore"]
        reranked.append(item)
    reranked.sort(key=lambda item: item["rerankScore"], reverse=True)
    for post_rank, item in enumerate(reranked, start=1):
        pre_rank = int(item.get("preRerankRank") or post_rank)
        rank_change = pre_rank - post_rank
        item["postRerankRank"] = post_rank
        item["rankChange"] = rank_change
        if rank_change > 0:
            direction = f"moved up {rank_change}"
        elif rank_change < 0:
            direction = f"moved down {abs(rank_change)}"
        else:
            direction = "unchanged"
        item["rerankExplanation"] = (
            f"preRank={pre_rank}, postRank={post_rank}, {direction}, "
            f"rerankScore={item['rerankScore']}"
        )
    return reranked[:limit]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return round(dot_product / (left_norm * right_norm), 4)


def run_query_embedding(query: str) -> list[float]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(embed_text(query))
    return []


def parse_embedding(value: str) -> list[float]:
    embedding = parse_json(value, [])
    if not isinstance(embedding, list):
        return []
    try:
        return [float(item) for item in embedding]
    except (TypeError, ValueError):
        return []


def retrieve_vector_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int,
    metadata_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    try:
        query_embedding = run_query_embedding(query)
    except Exception:
        return []
    if not query_embedding:
        return []

    store = SQLiteVectorStore(db)
    results = store.search(
        user_id=user_id,
        knowledge_base=knowledge_base,
        query_embedding=query_embedding,
        embedding_model=current_embedding_model(),
        limit=limit,
        metadata_filter=metadata_filter,
    )
    scored: list[dict[str, Any]] = []
    for result in results:
        scored.append(
            {
                "source": "database",
                "retrievalMode": "vector",
                "chunkId": result.chunk_id,
                "documentId": result.document_id,
                "knowledgeBase": result.knowledge_base,
                "title": result.title,
                "content": result.content,
                "score": result.score,
                "matchedTokens": [],
                "matchedKeywords": [],
                "metadata": result.metadata,
                "embeddingStatus": "ready",
                "embeddingModel": result.embedding_model,
                "documentStatus": result.document_status,
                "documentVisibility": result.document_visibility,
                **metadata_filter_hit_fields(metadata_filter),
            }
        )

    return scored


def retrieve_hybrid_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int,
    metadata_filter: dict[str, Any] | None = None,
    hybrid_weights: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    recall_limit = max(limit * 2, 6)
    bm25_hits = retrieve_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=recall_limit,
        mode="bm25",
        metadata_filter=metadata_filter,
    )
    vector_hits = retrieve_vector_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=recall_limit,
        metadata_filter=metadata_filter,
    )
    weights = normalize_hybrid_weights(hybrid_weights)
    return merge_hybrid_hits(
        bm25_hits,
        vector_hits,
        limit=limit,
        bm25_weight=weights["bm25"],
        vector_weight=weights["vector"],
    )


def run_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict[str, Any]]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(rerank_documents(query=query, documents=documents, top_n=top_n))
    return []


def retrieve_hybrid_rerank_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int,
    metadata_filter: dict[str, Any] | None = None,
    hybrid_weights: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    candidates = retrieve_hybrid_chunks(
        db,
        user_id=user_id,
        knowledge_base=knowledge_base,
        query=query,
        limit=max(limit * 3, 8),
        metadata_filter=metadata_filter,
        hybrid_weights=hybrid_weights,
    )
    if not candidates:
        return []
    documents = [hit_to_rerank_document(hit) for hit in candidates]
    try:
        results = run_rerank_documents(query, documents, limit)
    except Exception:
        return candidates[:limit]
    if not results:
        return candidates[:limit]
    return apply_rerank_results(candidates, results, limit=limit)


def retrieve_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int = 3,
    mode: str = "bm25",
    metadata_filter: dict[str, Any] | None = None,
    hybrid_weights: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if knowledge_base not in VALID_KNOWLEDGE_BASES or not str(query or "").strip():
        return []
    if mode == "vector":
        return retrieve_vector_chunks(
            db,
            user_id=user_id,
            knowledge_base=knowledge_base,
            query=query,
            limit=limit,
            metadata_filter=metadata_filter,
        )
    if mode == "hybrid":
        return retrieve_hybrid_chunks(
            db,
            user_id=user_id,
            knowledge_base=knowledge_base,
            query=query,
            limit=limit,
            metadata_filter=metadata_filter,
            hybrid_weights=hybrid_weights,
        )
    if mode == "hybrid_rerank":
        return retrieve_hybrid_rerank_chunks(
            db,
            user_id=user_id,
            knowledge_base=knowledge_base,
            query=query,
            limit=limit,
            metadata_filter=metadata_filter,
            hybrid_weights=hybrid_weights,
        )
    if mode != "bm25":
        return []

    chunks = list(
        db.scalars(
            select(RagChunk)
            .join(RagDocument, RagChunk.document_id == RagDocument.id)
            .where(*visible_enabled_chunk_filters(user_id, knowledge_base))
            .order_by(RagChunk.created_at.desc(), RagChunk.id.desc())
            .limit(120)
        ).all()
    )
    chunks = filter_chunks_by_metadata(chunks, metadata_filter)
    if not chunks:
        return []

    query_tokens = tokenize(query)
    corpus_tokens = [tokenize(chunk_text(chunk)) for chunk in chunks]
    scored: list[dict[str, Any]] = []

    for chunk, document_tokens in zip(chunks, corpus_tokens, strict=False):
        score = bm25_score(query_tokens, document_tokens, corpus_tokens)
        if score <= 0:
            continue
        scored.append(
            {
                "source": "database",
                "retrievalMode": "bm25",
                "chunkId": chunk.id,
                "documentId": chunk.document_id,
                "knowledgeBase": chunk.knowledge_base,
                "title": chunk.title,
                "content": chunk.content,
                "score": score,
                "matchedTokens": matched_tokens(query_tokens, document_tokens),
                "matchedKeywords": matched_tokens(query_tokens, tokenize(" ".join(parse_json(chunk.keywords_json, [])))),
                "metadata": parse_json(chunk.metadata_json, {}),
                **document_lifecycle_fields(chunk),
                **metadata_filter_hit_fields(metadata_filter),
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
