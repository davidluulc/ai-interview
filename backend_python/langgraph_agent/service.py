from typing import Any

from .checkpoint import summarize_checkpoint
from .graph import run_interview_graph_v2


async def run_langgraph_agent_v2(**kwargs: Any) -> dict[str, Any]:
    return await run_interview_graph_v2(**kwargs)


def get_langgraph_checkpoint_summary(thread_id: str) -> dict[str, Any]:
    return summarize_checkpoint(thread_id)
