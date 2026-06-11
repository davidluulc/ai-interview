import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend_python.database import SessionLocal, init_db
from backend_python.rag_evaluation import evaluate_modes
from backend_python.rag_evaluation_seed import seed_evaluation_documents
from backend_python.retrieval_service import retrieve_chunks
import backend_python.retrieval_service as retrieval_service

CASE_PATH = ROOT_DIR / "data" / "rag_evaluation_cases.json"
DEFAULT_MODES = ["bm25", "vector", "hybrid", "hybrid_rerank"]
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation.")
    parser.add_argument("--mock-vector", action="store_true", help="Use deterministic evaluation embeddings.")
    return parser.parse_args(argv)


def load_cases(path: Path = CASE_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_result(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def build_mock_query_embedding(case: dict) -> list[float]:
    return MOCK_QUERY_EMBEDDINGS.get(str(case.get("id") or ""), [1.0, 0.0, 0.0])


def ensure_evaluation_seed_documents(db, *, user_id: int) -> int:
    return seed_evaluation_documents(db, user_id=user_id)


def install_mock_vector_clients(case: dict) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return build_mock_query_embedding(case)

    async def fake_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict]:
        return [{"index": index, "relevance_score": float(top_n - index)} for index in range(min(top_n, len(documents)))]

    retrieval_service.embed_text = fake_embed_text
    retrieval_service.rerank_documents = fake_rerank_documents


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    init_db()
    cases = load_cases()
    with SessionLocal() as db:
        user_id = 1
        ensure_evaluation_seed_documents(db, user_id=user_id)

        def retriever(case: dict, mode: str, k: int) -> list[dict]:
            if args.mock_vector:
                install_mock_vector_clients(case)
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
