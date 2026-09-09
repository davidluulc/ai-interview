"""Re-embed all ready chunks with current embedding settings.

One-off ops script for the 2026-09-09 pgvector cutover: production embeddings
were 1024-dim while the migration column is vector(2048). Re-embeds every
ready chunk with the current provider settings (zhipu embedding-3 @ 2048),
double-writing embedding_json and embedding_vec via PgVectorStore.upsert_embedding.
Idempotent; verifies each vector's dimension and stops loudly on mismatch.

Usage (in the app container): python scripts/reembed_embeddings.py
"""
import asyncio
import sys

from sqlalchemy import text

from backend_python.config import EMBEDDING_DIMENSIONS_INT
from backend_python.database import SessionLocal
from backend_python.embedding_client import embed_text
from backend_python.pg_vector_store import PgVectorStore


def main() -> int:
    db = SessionLocal()
    store = PgVectorStore(db)
    rows = db.execute(
        text(
            "SELECT id, content, embedding_model FROM rag_chunks "
            "WHERE embedding_status = 'ready' ORDER BY id"
        )
    ).fetchall()
    print(f"chunks_to_reembed={len(rows)} expected_dimensions={EMBEDDING_DIMENSIONS_INT}")
    done = failed = 0
    for chunk_id, content, model in rows:
        try:
            embedding = asyncio.run(embed_text(content))
        except Exception as exc:
            print(f"chunk {chunk_id}: embed_text FAILED: {exc}")
            failed += 1
            continue
        if len(embedding) != EMBEDDING_DIMENSIONS_INT:
            print(
                f"chunk {chunk_id}: dimension mismatch provider={len(embedding)} "
                f"expected={EMBEDDING_DIMENSIONS_INT} — STOP"
            )
            return 1
        store.upsert_embedding(chunk_id=chunk_id, embedding=embedding, model=model)
        done += 1
        print(f"chunk {chunk_id}: ok dim={len(embedding)}")
    print(f"reembedded={done} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
