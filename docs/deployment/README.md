# 部署文档总览

本目录用于记录 AI 模拟面试系统的上线展示 V1 部署流程。

推荐阅读顺序：

1. `vps-deploy-v1.md`：从一台新的 Ubuntu VPS 部署项目。
2. `nginx-cloudflare-https.md`：理解域名、DNS、Cloudflare、Nginx 和 HTTPS。
3. `troubleshooting.md`：部署失败时如何定位问题。
4. `backup-and-rollback.md`：如何备份数据库、回滚代码和恢复服务。

本阶段目标是让项目具备“可上线展示、可复现、可排错”的能力，不追求 Kubernetes、复杂 CI/CD、监控告警平台或大陆服务器备案。

核心链路：

```text
GitHub -> VPS -> Docker Compose -> Nginx -> FastAPI -> PostgreSQL / Redis / Celery
```

敏感信息规则：

- `.env.production` 只能放在服务器本地，不提交 Git。
- `.env.production.example` 只放占位符。
- 不在文档中写真实 API Key、真实数据库密码、真实服务器 IP。
