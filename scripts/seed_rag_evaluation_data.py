import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend_python.database import SessionLocal, init_db
from backend_python.rag_evaluation_seed import seed_evaluation_documents


def main() -> None:
    init_db()
    with SessionLocal() as db:
        count = seed_evaluation_documents(db, user_id=1)
    print(f"Seeded {count} RAG evaluation documents for user_id=1.")


if __name__ == "__main__":
    main()
