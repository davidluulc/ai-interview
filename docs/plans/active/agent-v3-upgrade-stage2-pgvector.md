# Agent v3 Stage 2：pgvector 向量检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 向量检索从「全量拉回 Python 逐条算余弦 + created_at 截断 200 条」升级为 pgvector 的 SQL 内余弦距离 + HNSW 索引；SQLiteVectorStore 保留为回滚/对照路径，配置开关切换。

**Architecture:** 新增 `PgVectorStore`（实现既有 `VectorStore` Protocol，raw SQL 实现，**不引入 pgvector python 适配包**）；Alembic 迁移给 `rag_chunks` 加 `embedding_vec vector(N)` 列（JSON 列保留双写）；唯一接线点 `retrieval_service.py:334` 按 `VECTOR_SEARCH_BACKEND=pgvector|sqlite` 选择实现。集成测试经 `TEST_DATABASE_URL` 门控，跑在 docker 一次性 pgvector 容器上。

**Tech Stack:** PostgreSQL 16 + pgvector 扩展（镜像 `pgvector/pgvector:pg16` 已拉取）、SQLAlchemy 2.0 text() 原生 SQL、alembic、pytest。**不新增 Python 依赖。**

**上游 spec:** `docs/specs/active/agent-v3-upgrade-design.md` §4-S2、§0 Goal Card。

## Global Constraints

- 不新增 Python 依赖（vector 列读写用 raw SQL + `'[1,2,...]'::vector` 文本转型，不用 pgvector 的 SQLAlchemy 适配包）。
- 不改 `SQLiteVectorStore` 任何现有行为（它是回滚路径）；不改既有测试。
- 迁移只加列不改列；`embedding_json` 双写保留。
- `VECTOR_SEARCH_BACKEND` 默认 `sqlite`（本阶段结束前不切默认，公网部署窗口验证后再切）。
- 测试命令：`.venv/bin/python -m pytest -q`；已知基线失败 1 个（README 断言，main 遗留）。
- 分支 `feat/agent-v3-s2-pgvector`，提交 conventional commits，不 push。

## 预先完成的环境事实（写作本计划时已验证）

- docker 守护进程可用（29.3.1），`pgvector/pgvector:pg16` 镜像已拉取。
- embedding 维度由 `EMBEDDING_DIMENSIONS` 环境变量控制（`embedding_client.py:83`），未设时用 provider 默认。迁移列宽取 `EMBEDDING_DIMENSIONS` 或 `2048`（生产 zhipu embedding-3 默认），见 Task 1。

## File Map

- Create: `backend_python/pg_vector_store.py` — PgVectorStore（upsert_embedding / search）
- Create: `alembic/versions/20260909_0001_add_rag_chunks_embedding_vec.py` — 加列 + HNSW 索引
- Create: `scripts/pgvector_test_db.sh` — 起/停一次性测试库
- Create: `scripts/backfill_embedding_vec.py` — 存量 JSON 回填
- Create: `tests/test_pg_vector_store.py` — 单元（纯函数）+ 集成（TEST_DATABASE_URL 门控）
- Modify: `backend_python/config.py` — VECTOR_SEARCH_BACKEND / EMBEDDING_DIMENSIONS_INT
- Modify: `backend_python/retrieval_service.py:334` — 按开关选 store
- Modify: `docker-compose.yml` — db 镜像 postgres:16 → pgvector/pgvector:pg16
- Modify: `.env.example` / `.env.production.example` — 新增两个变量
- Modify: `docs/roadmap/current-state.md` — 指针与阶段记录

---

### Task 1: 测试库脚本 + 配置开关

**Files:**
- Create: `scripts/pgvector_test_db.sh`
- Modify: `backend_python/config.py`

**Interfaces:**
- Produces: `config.VECTOR_SEARCH_BACKEND`（默认 "sqlite"）；`config.EMBEDDING_DIMENSIONS_INT`（int，默认 2048）；测试库经 `TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:55432/ai_interview_test` 可用。

- [ ] **Step 1: 写测试库脚本**

`scripts/pgvector_test_db.sh`：

```bash
#!/usr/bin/env bash
# 一次性 pgvector 测试库：起容器 → 建库建扩展 → 退出码 0
# 用法: ./scripts/pgvector_test_db.sh up | down
set -euo pipefail
CONTAINER=ai-interview-pgvector-test
PORT=55432

case "${1:-}" in
  up)
    docker run -d --name "$CONTAINER" -e POSTGRES_PASSWORD=ai_interview \
      -e POSTGRES_USER=ai_interview -e POSTGRES_DB=ai_interview_test \
      -p "$PORT":5432 pgvector/pgvector:pg16 >/dev/null
    for _ in $(seq 1 30); do
      docker exec "$CONTAINER" pg_isready -U ai_interview -d ai_interview_test >/dev/null 2>&1 && break
      sleep 1
    done
    docker exec "$CONTAINER" psql -U ai_interview -d ai_interview_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
    echo "TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:${PORT}/ai_interview_test"
    ;;
  down)
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    echo "removed"
    ;;
  *) echo "usage: $0 up|down" >&2; exit 1 ;;
esac
```

`chmod +x` 后执行 `./scripts/pgvector_test_db.sh up`，记录输出的 URL。

- [ ] **Step 2: config 增加两个动态配置**

`backend_python/config.py` 追加：

```python
VECTOR_SEARCH_BACKEND = os.getenv("VECTOR_SEARCH_BACKEND", "sqlite").strip().lower()
EMBEDDING_DIMENSIONS_INT = int(os.getenv("EMBEDDING_DIMENSIONS") or 2048)
```

- [ ] **Step 3: 验证并提交**

```bash
.venv/bin/python -c "from backend_python.config import VECTOR_SEARCH_BACKEND, EMBEDDING_DIMENSIONS_INT; print(VECTOR_SEARCH_BACKEND, EMBEDDING_DIMENSIONS_INT)"
```

Expected: `sqlite 2048`。commit：`feat: add pgvector test db script and backend switch config`

### Task 2: Alembic 迁移（加列 + 索引）

**Files:**
- Create: `alembic/versions/20260909_0001_add_rag_chunks_embedding_vec.py`

**Interfaces:**
- Produces: `rag_chunks.embedding_vec` 列（vector(2048)，nullable）+ `ix_rag_chunks_embedding_vec_hnsw` HNSW 索引（vector_cosine_ops）。

- [ ] **Step 1: 写迁移**

（down_revision 填当前链尾——执行时用 `ls alembic/versions/ | tail -1` 确认最后一个 revision id）

```python
"""add rag_chunks.embedding_vec with hnsw index

Revision ID: 20260909_0001
Revises: <执行时确认当前链尾>
"""

from alembic import op

revision = "20260909_0001"
down_revision = "<执行时确认>"
branch_labels = None
depends_on = None

DIMENSIONS = 2048


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"ALTER TABLE rag_chunks ADD COLUMN embedding_vec vector({DIMENSIONS})")
    op.execute(
        "CREATE INDEX ix_rag_chunks_embedding_vec_hnsw ON rag_chunks "
        "USING hnsw (embedding_vec vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_vec_hnsw")
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS embedding_vec")
```

- [ ] **Step 2: 在测试库上验证 up/down**

```bash
TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:55432/ai_interview_test \
  .venv/bin/python -m alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:55432/ai_interview_test \
  .venv/bin/python -m alembic downgrade -1 && \
TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:55432/ai_interview_test \
  .venv/bin/python -m alembic upgrade head
```

（若 alembic env.py 不读 TEST_DATABASE_URL，先读 `alembic/env.py` 并按其现有机制让测试 URL 生效——通常是 `os.getenv` 覆盖 `sqlalchemy.url`；保持与现有机制一致，勿重构。）

Expected: 三条命令全部 exit 0。commit：`feat: add embedding_vec column migration with hnsw index`

### Task 3: PgVectorStore 实现（TDD，集成门控）

**Files:**
- Create: `backend_python/pg_vector_store.py`
- Create: `tests/test_pg_vector_store.py`

**Interfaces:**
- Consumes: `VectorStore` Protocol（vector_store.py:28）、`VectorSearchResult`、`parse_embedding`、`chunk_matches_metadata_filter`。
- Produces:

```python
def build_pg_dsn() -> str  # TEST_DATABASE_URL 或 DATABASE_URL
def embedding_literal(values: list[float]) -> str  # '[0.1,0.2]' 文本
class PgVectorStore:  # __init__(self, db: Session)；实现 Protocol 两个方法
```

行为契约：`search` 用 `ORDER BY embedding_vec <=> (:q)::vector LIMIT :limit`，WHERE 条件与 SQLiteVectorStore 等价（knowledge_base、embedding_status='ready'、document enabled、owner/public、可选 embedding_model）；metadata 过滤在 Python 侧复用 `chunk_matches_metadata_filter`（与 SQLite 实现一致）；score = `1 - 距离`（余弦距离转相似度，保留 4 位）。**排序差异免责**：不再有「优先本人文档」的 Python 二次排序，改为 SQL 纯按距离（行为差异写入文档与测试断言）。

- [ ] **Step 1: 写门控的集成测试**（无 TEST_DATABASE_URL 时整文件 skip，保证默认套件绿）

```python
import os
import uuid

import pytest

from backend_python.database import SessionLocal  # noqa: F401  确认导入路径与现有测试一致
from backend_python.db_models import RagChunk, RagDocument, User

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="pgvector integration tests need TEST_DATABASE_URL"
)
```

测试内容（3 个）：upsert 后 search 按 `<=>` 距离返回最相近 chunk 且 score=1-距离；metadata_filter 过滤生效；owner/public 可见性与 SQLite 版等价。构造数据复用 `tests/test_vector_store_contract.py` 的建用户/文档/chunk 辅助函数模式（复制局部实现，不改旧文件）。

- [ ] **Step 2: 红灯验证**

```bash
./scripts/pgvector_test_db.sh up
TEST_DATABASE_URL=postgresql+psycopg://ai_interview:ai_interview@localhost:55432/ai_interview_test \
  .venv/bin/python -m pytest tests/test_pg_vector_store.py -q
```

Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现 PgVectorStore**（raw SQL，`db.execute(text(...))`；upsert 用 `UPDATE rag_chunks SET embedding_vec = :vec ::vector, ...`；search 查询列含 chunk/document 全部 VectorSearchResult 需要的字段）

- [ ] **Step 4: 绿灯 + 全量回归**（不带 TEST_DATABASE_URL 跑全量 → 新文件 skip，其余 467+1 基线不变）

- [ ] **Step 5: commit**：`feat: add pgvector store with sql cosine search`

### Task 4: 接线（开关选择）+ 一致性对照测试

**Files:**
- Modify: `backend_python/retrieval_service.py:330-340`（retrieve_vector_chunks 内）
- Create: `tests/test_vector_backend_switch.py`

- [ ] **Step 1: 修改接线点**

```python
    from .config import VECTOR_SEARCH_BACKEND
    from .pg_vector_store import PgVectorStore

    store = PgVectorStore(db) if VECTOR_SEARCH_BACKEND == "pgvector" else SQLiteVectorStore(db)
```

（import 放文件顶部，遵循现有 import 风格。）

- [ ] **Step 2: 一致性测试**（门控同 Task 3）：同一组 chunk 数据 + 同一 query_embedding，两个 backend 的 top-1 chunkId 一致、top-k 集合重合率 ≥ 2/3（容忍顺序与截断差异）；开关为 sqlite 时不触碰 PgVectorStore（monkeypatch 证明）。

- [ ] **Step 3: 全量回归 + commit**：`feat: switch vector backend by config with parity test`

### Task 5: 双写 + 回填脚本 + 编排收尾

**Files:**
- Modify: `backend_python/pg_vector_store.py`（无需——双写在 upsert 已覆盖；此任务改 `rag_ingestion` 路径确认走 `upsert_embedding` 即可——grep 确认 `SQLiteVectorStore.upsert_embedding` 的所有调用方，若 ingestion 直接写 `embedding_json` 字段而非经 store，则在同处补 `embedding_vec` 双写）
- Create: `scripts/backfill_embedding_vec.py`
- Modify: `docker-compose.yml`（db image 两处：`postgres:16` → `pgvector/pgvector:pg16`）
- Modify: `.env.example` / `.env.production.example`（`VECTOR_SEARCH_BACKEND=sqlite`、`EMBEDDING_DIMENSIONS=2048` + 注释）
- Modify: `docs/roadmap/current-state.md`（S2 完成记录 + 待办：公网部署窗口执行 `alembic upgrade head` + 回填 + 灰度切 pgvector + HNSW 过滤退化观察）

`scripts/backfill_embedding_vec.py` 核心逻辑（幂等，按 embedding_model 分组跳过长度 ≠ EMBEDDING_DIMENSIONS_INT 的行并计数告警）：

```python
import sys

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
            text("UPDATE rag_chunks SET embedding_vec = :vec::vector WHERE id = :id"),
            {"vec": embedding_literal(values), "id": chunk_id},
        )
        done += 1
    db.commit()
    print(f"backfilled={done} skipped_dimension_mismatch={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

验证：全量 pytest（新文件在无 TEST_DATABASE_URL 时 skip）→ `docker compose --env-file .env.production.example config --quiet` exit 0 → commit `feat: double-write embedding vec with backfill script and compose image`

### Task 6: 阶段收尾

- [ ] 全量测试 + compose 校验（预期：467+1 基线 + 新增测试；集成文件在 CI 无库时 skip）
- [ ] `current-state.md` 记录（含「排序行为差异：pgvector 路径无本人优先二次排序」「HNSW+强过滤退化限制」两个面试话术点）
- [ ] commit `docs: record stage2 pgvector completion`
- [ ] 合并门：终审 clean → merge main → 删分支（按流水线总控执行）

## Self-Review（写作时已执行）

- Spec §4-S2 验收三条（一致性测试 / 回填 / 限制文档）分别由 Task 4 / Task 5 / Task 6 覆盖。
- 两个 `<执行时确认>` 占位（迁移链尾 revision、alembic env.py 的 URL 机制）均为「执行首日 1 分钟可查」的事实型占位，非设计缺口。
- 红线核对：无新 Python 依赖 ✅；SQLiteVectorStore 零改动 ✅；迁移只加列 ✅；默认 sqlite ✅。
