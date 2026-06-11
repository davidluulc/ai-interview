import json
import re
from typing import Any

from .config import ROOT_DIR

POSITION_TEMPLATE_PATH = ROOT_DIR / "data" / "position_templates.json"


def load_position_templates() -> list[dict[str, Any]]:
    if not POSITION_TEMPLATE_PATH.exists():
        return []

    return json.loads(POSITION_TEMPLATE_PATH.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", text.lower())
    seen = set()
    result = []
    for token in tokens:
        if token not in seen:
            result.append(token)
            seen.add(token)
    return result


def build_agent_query(profile: dict[str, Any], target_direction: str = "") -> str:
    return " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
            str(profile.get("company") or ""),
            target_direction,
        ]
    )


def score_template(template: dict[str, Any], query: str, tokens: list[str]) -> dict[str, Any]:
    query_lower = normalize_text(query)
    matched_skills: list[str] = []
    matched_keywords: list[str] = []
    score = 0.0

    for skill in template.get("core_skills", []):
        skill_text = normalize_text(skill)
        if skill_text and skill_text in query_lower:
            matched_skills.append(str(skill))
            score += 5.0

    for skill in template.get("nice_to_have_skills", []):
        skill_text = normalize_text(skill)
        if skill_text and skill_text in query_lower:
            matched_skills.append(str(skill))
            score += 2.0

    keyword_fields = [
        "project_keywords",
        "focus_topics",
        "recommended_query_keywords",
    ]
    for field in keyword_fields:
        for keyword in template.get(field, []):
            keyword_text = normalize_text(keyword)
            if keyword_text and keyword_text in query_lower:
                matched_keywords.append(str(keyword))
                score += 3.0

    text = " ".join(
        [
            str(template.get("title") or ""),
            str(template.get("category") or ""),
            str(template.get("position_tag") or ""),
            " ".join(template.get("core_skills", [])),
            " ".join(template.get("focus_topics", [])),
        ]
    ).lower()
    for token in tokens:
        if token in text:
            score += 0.8

    return {
        "score": round(score, 2),
        "matchedSkills": matched_skills,
        "matchedKeywords": matched_keywords,
    }


def match_positions(profile: dict[str, Any], target_direction: str = "", limit: int = 3) -> list[dict[str, Any]]:
    query = build_agent_query(profile, target_direction)
    tokens = tokenize(query)
    results = []

    for template in load_position_templates():
        evidence = score_template(template, query, tokens)
        if evidence["score"] <= 0:
            continue

        reason_parts = []
        if evidence["matchedSkills"]:
            reason_parts.append(f"匹配技能：{'、'.join(evidence['matchedSkills'][:5])}")
        if evidence["matchedKeywords"]:
            reason_parts.append(f"匹配项目/方向：{'、'.join(evidence['matchedKeywords'][:5])}")

        results.append(
            {
                **template,
                "score": evidence["score"],
                "matchedSkills": evidence["matchedSkills"],
                "matchedKeywords": evidence["matchedKeywords"],
                "reason": "；".join(reason_parts) or "与简历/JD 存在关键词重合",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
