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
