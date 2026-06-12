# 备份与回滚手册

## 1. 为什么要备份

上线后，代码可以从 GitHub 重新拉取，但数据库里的用户、面试记录、RAG 文档和训练任务不能随便丢。

所以部署时至少要考虑两类恢复：

- 数据库备份与恢复。
- 代码版本回滚。

## 2. PostgreSQL 备份

备份到当前目录：

```bash
docker compose -p ai-interview exec db pg_dump -U ai_interview ai_interview > backup_ai_interview.sql
```

建议把备份文件再复制到服务器外部，例如对象存储、本地电脑或另一台机器。

不要把备份文件提交到 GitHub。

## 3. PostgreSQL 恢复

恢复前先确认你真的要覆盖当前数据。

```bash
cat backup_ai_interview.sql | docker compose -p ai-interview exec -T db psql -U ai_interview ai_interview
```

恢复后检查：

```bash
docker compose -p ai-interview exec app alembic current
docker compose -p ai-interview logs app --tail=100
```

## 4. 代码回滚

查看提交：

```bash
git log --oneline -5
```

回到指定版本：

```bash
git checkout <commit_id>
docker compose -p ai-interview --env-file .env.production up -d --build
```

如果数据库表结构也发生过变化，必须同时考虑 Alembic 迁移版本，不能只回滚代码。

## 5. 常规更新前的安全流程

每次上线前建议：

```bash
git status
git pull
docker compose -p ai-interview exec db pg_dump -U ai_interview ai_interview > backup_before_release.sql
docker compose -p ai-interview --env-file .env.production up -d --build
docker compose -p ai-interview --env-file .env.production exec app alembic upgrade head
docker compose -p ai-interview ps
```

## 6. `.env.production` 备份注意

`.env.production` 包含 API Key、数据库密码和 JWT SECRET，不应该提交到 GitHub。

可以用安全方式保存，例如：

- 密码管理器。
- 云厂商密钥管理。
- 本机加密备份。

不要截图发到公开平台。
