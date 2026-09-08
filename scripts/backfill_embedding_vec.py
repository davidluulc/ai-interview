import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend_python.config import EMBEDDING_DIMENSIONS_INT
from backend_python.database import SessionLocal
from backend_python.pg_vector_store import PgVectorStore, embedding_literal
from backend_python.vector_store import parse_embedding
from sqlalchemy import text


def main() -> int:
    db = SessionLocal()
    rows = db.execute(
        text("SELECT id, embedding_json FROM rag_chunks WHERE embedding_vec IS NULL AND embedding_json != '[]'")
    ).fetchall()
    skipped, done = 0, 0
    for chunk_id, embedding_json in rows:
        values = parse_embedding(embedding_json)
        if len(values) != EMBEDDING_DIMENSIONS_INT:
            skipped += 1
            continue
        db.execute(
            # CAST form: text() does not bind ":param::type" (see pg_vector_store.py)
            text("UPDATE rag_chunks SET embedding_vec = CAST(:vec AS vector) WHERE id = :id"),
            {"vec": embedding_literal(values), "id": chunk_id},
        )
        done += 1
    db.commit()
    print(f"backfilled={done} skipped_dimension_mismatch={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
