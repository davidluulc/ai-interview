from typing import Any


def compact_text(*parts: Any) -> str:
    return " ".join(str(part or "").strip() for part in parts if str(part or "").strip())


def append_variant(
    variants: list[dict[str, str]],
    *,
    name: str,
    query: str,
    seen: set[str],
) -> None:
    normalized_query = compact_text(query)
    dedupe_key = normalized_query.lower()
    if not normalized_query or dedupe_key in seen:
        return
    variants.append({"name": name, "query": normalized_query})
    seen.add(dedupe_key)


def build_query_variants(
    query: str,
    *,
    profile: dict[str, Any] | None = None,
    stage: str = "",
    weakness_tags: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, str]]:
    profile = profile or {}
    weakness_tags = weakness_tags or []
    variants: list[dict[str, str]] = []
    seen: set[str] = set()

    append_variant(variants, name="base", query=query, seen=seen)
    append_variant(
        variants,
        name="role",
        query=compact_text(
            query,
            profile.get("targetRole"),
            profile.get("positionTag"),
            profile.get("jd"),
        ),
        seen=seen,
    )
    append_variant(
        variants,
        name="stage",
        query=compact_text(query, profile.get("targetRole"), profile.get("positionTag"), stage),
        seen=seen,
    )
    append_variant(
        variants,
        name="weakness",
        query=compact_text(query, profile.get("positionTag"), " ".join(str(tag) for tag in weakness_tags)),
        seen=seen,
    )

    return variants[: max(limit, 1)]
