"""add rag_chunks.embedding_vec with hnsw index

Revision ID: 20260909_0001
Revises: 20260619_0001
"""

from alembic import op

revision = "20260909_0001"
down_revision = "20260619_0001"
branch_labels = None
depends_on = None

DIMENSIONS = 2048


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"ALTER TABLE rag_chunks ADD COLUMN embedding_vec vector({DIMENSIONS})")
    # pgvector HNSW indexes cap at 2000 dimensions for `vector` columns; at
    # DIMENSIONS=2048 the index must be built on a halfvec cast (limit 4000).
    # Storage stays full-precision vector(2048); indexed scans require queries
    # to ORDER BY (embedding_vec::halfvec(2048)) <=> (:q)::halfvec(2048).
    op.execute(
        "CREATE INDEX ix_rag_chunks_embedding_vec_hnsw ON rag_chunks "
        f"USING hnsw ((embedding_vec::halfvec({DIMENSIONS})) halfvec_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_vec_hnsw")
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS embedding_vec")
