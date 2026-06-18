# PostgreSQL Compatibility V4

## 结论

本地开发默认 SQLite，保证启动快、环境简单。生产环境推荐 PostgreSQL，适合多人系统、并发读写、事务、复杂查询和后续 pgvector 扩展。

## 不一刀切替换 SQLite 的原因

- Windows 本地安装和服务管理成本更高。
- 测试链路更慢。
- 迁移脚本要求更严。
- 新手开发时容易被数据库连接、端口、权限和编码问题卡住。

因此项目采用“本地轻量 + 生产兼容”的路线：

```text
本地默认 SQLite
生产配置支持 PostgreSQL
Docker Compose 可启动 PostgreSQL
测试覆盖 DATABASE_URL 识别、URL 脱敏和 engine 配置
```

## 本地 SQLite 默认配置

`.env.example` 默认保留：

```env
DATABASE_URL=sqlite:///data/app.db
AUTO_INIT_DB=true
```

这适合日常开发、学习和快速调试。

## PostgreSQL 生产配置

`.env.production.example` 使用：

```env
POSTGRES_DB=ai_interview
POSTGRES_USER=ai_interview
POSTGRES_PASSWORD=replace_with_postgres_password
DATABASE_URL=postgresql+psycopg://ai_interview:replace_with_postgres_password@db:5432/ai_interview
AUTO_INIT_DB=false
```

`AUTO_INIT_DB=false` 表示生产环境不依赖 `metadata.create_all()` 自动建表，后续应通过 Alembic 迁移管理数据库结构。

## Docker PostgreSQL 示例

```powershell
docker compose up -d db
```

确认数据库服务健康后，再启动 app、worker、redis 和 nginx。

## 面试表达

我没有直接把本地开发环境强制切到 PostgreSQL，因为这会增加安装、建库、端口和权限问题，拖慢日常开发。项目采用本地 SQLite、生产 PostgreSQL 兼容的策略：本地启动快，生产环境又能通过 `DATABASE_URL` 和 Docker Compose 切换到 PostgreSQL。
