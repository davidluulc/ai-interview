# Database Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Alembic migration support while keeping SQLite as the default local database and preserving PostgreSQL readiness through `DATABASE_URL`.

**Architecture:** SQLAlchemy remains the ORM layer and runtime database access path. Alembic is added as a schema migration tool that imports `backend_python.database.Base` and `backend_python.db_models` metadata, then manages versioned migration scripts under `alembic/versions`.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, pytest, SQLite by default, PostgreSQL-compatible configuration.

---

## File Structure

- Modify `requirements.txt`: add `alembic` and `psycopg[binary]`.
- Create `alembic.ini`: Alembic command configuration.
- Create `alembic/env.py`: connects Alembic to project settings and SQLAlchemy metadata.
- Create `alembic/script.py.mako`: default migration template.
- Create `alembic/versions/20260603_0001_create_interview_records.py`: first migration.
- Create `tests/test_database_migrations.py`: checks migration files and model structure.
- Modify `README.md`: add Chinese Alembic and PostgreSQL notes.
- Modify `.env.example`: add a commented PostgreSQL `DATABASE_URL` example.

---

### Task 1: Add Migration Structure Tests

**Files:**
- Create: `tests/test_database_migrations.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from backend_python.db_models import InterviewRecord


def test_interview_record_model_declares_expected_table_and_columns() -> None:
    columns = InterviewRecord.__table__.columns

    assert InterviewRecord.__tablename__ == "interview_records"
    assert "id" in columns
    assert "candidate_name" in columns
    assert "target_role" in columns
    assert "application_type" in columns
    assert "mode" in columns
    assert "depth" in columns
    assert "score" in columns
    assert "profile_json" in columns
    assert "answers_json" in columns
    assert "report_json" in columns
    assert "created_at" in columns


def test_alembic_configuration_files_exist() -> None:
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
    assert Path("alembic/script.py.mako").exists()


def test_initial_interview_records_migration_exists() -> None:
    migration_files = list(Path("alembic/versions").glob("*create_interview_records.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "create_table" in migration_text
    assert "interview_records" in migration_text
    assert "candidate_name" in migration_text
    assert "report_json" in migration_text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_database_migrations.py -q
```

Expected: model test passes, Alembic file tests fail because migration files do not exist yet.

---

### Task 2: Add Alembic Dependency And Configuration

**Files:**
- Modify: `requirements.txt`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`

- [ ] **Step 1: Add dependencies**

Add these lines to `requirements.txt`:

```text
alembic==1.14.0
psycopg[binary]==3.2.3
```

- [ ] **Step 2: Create `alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
path_separator = os
sqlalchemy.url = sqlite:///data/app.db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create `alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend_python.config import DATABASE_URL
from backend_python.database import Base
from backend_python import db_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Run migration structure test**

Run:

```bash
python -m pytest tests/test_database_migrations.py -q
```

Expected: migration config tests pass, initial migration test still fails.

---

### Task 3: Add Initial Migration

**Files:**
- Create: `alembic/versions/20260603_0001_create_interview_records.py`

- [ ] **Step 1: Create migration file**

```python
"""create interview records table

Revision ID: 20260603_0001
Revises:
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_name", sa.String(length=100), nullable=False),
        sa.Column("target_role", sa.String(length=200), nullable=False),
        sa.Column("application_type", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("depth", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_records_id"), "interview_records", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_records_id"), table_name="interview_records")
    op.drop_table("interview_records")
```

- [ ] **Step 2: Run migration structure test**

Run:

```bash
python -m pytest tests/test_database_migrations.py -q
```

Expected: all migration tests pass.

---

### Task 4: Update Docs And Environment Example

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Update `.env.example`**

Keep SQLite as the active default and add a commented PostgreSQL example:

```text
DATABASE_URL=sqlite:///data/app.db
# PostgreSQL example for deployment:
# DATABASE_URL=postgresql+psycopg://ai_interview:your_password@127.0.0.1:5432/ai_interview
```

- [ ] **Step 2: Update README database section**

Add a Chinese section explaining:

```markdown
## 数据库迁移

当前本地默认使用 SQLite：

```text
DATABASE_URL=sqlite:///data/app.db
```

如果未来上线到云服务器，可以切换为 PostgreSQL：

```text
DATABASE_URL=postgresql+psycopg://ai_interview:your_password@127.0.0.1:5432/ai_interview
```

Alembic 用来管理数据库表结构版本。常用命令：

```bash
alembic upgrade head
alembic current
alembic history
```

`Base.metadata.create_all()` 适合本地快速开发，Alembic 更适合上线环境和团队协作。
```

- [ ] **Step 3: Run tests**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

---

### Task 5: Final Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Install dependencies if needed**

Run:

```bash
python -m pip install -r requirements.txt
```

Expected: installation succeeds.

- [ ] **Step 2: Run full tests**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Verify Alembic can inspect migration history**

Run:

```bash
python -m alembic history
```

Expected: output includes `20260603_0001 -> create interview records table`.

- [ ] **Step 4: Verify FastAPI import**

Run:

```bash
python -c "from backend_python.main import app; print(app.title)"
```

Expected: `AI Mock Interview System`.

- [ ] **Step 5: Check git diff**

Run:

```bash
git diff -- requirements.txt alembic.ini alembic backend_python tests README.md .env.example
```

Expected: diff only contains Alembic migration support, tests, and documentation updates.
