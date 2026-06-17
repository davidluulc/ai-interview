from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .checkpoint_store import build_checkpoint_summary, checkpoint_summary_store, normalize_thread_id

memory_saver = MemorySaver()


def build_graph_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": normalize_thread_id(thread_id)}}


def record_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    summary = build_checkpoint_summary(thread_id=thread_id, state=state)
    return checkpoint_summary_store.save_summary(summary)


def summarize_checkpoint(thread_id: str) -> dict[str, Any]:
    return checkpoint_summary_store.get_summary(thread_id)
