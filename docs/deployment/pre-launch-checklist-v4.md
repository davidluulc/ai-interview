# Pre-Launch Checklist V4

- [ ] `.env.production` 不包含占位密钥。
- [ ] `SECRET_KEY` 已替换为强随机值。
- [ ] DashScope API key 没有提交到 Git。
- [ ] PostgreSQL 连接可用。
- [ ] Redis 连接可用。
- [ ] Celery worker 已启动并能消费 RAG ingestion task。
- [ ] Nginx `/api/*` 正确代理到 FastAPI。
- [ ] Vue3 页面可访问。
- [ ] 管理员后台可看到基础设施、RAG ingestion、Agent workflow 状态。
- [ ] 已准备数据库备份方案。
- [ ] 已准备回滚方案。
- [ ] 已记录常见故障排查入口。

## 回滚建议

上线前保留最近一个稳定 Git commit。部署失败时，回退到稳定 commit，重新构建镜像并重启 app、worker 和 nginx。

## 面试表达

上线前我会用 checklist 检查密钥、数据库、Redis、Celery worker、Nginx 代理、前端页面和回滚方案。这样不是只让项目在本地能跑，而是让它具备可部署、可排错、可恢复的工程闭环。
