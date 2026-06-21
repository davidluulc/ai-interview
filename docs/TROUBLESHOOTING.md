# 排障总入口

本文是公开排障短入口。详细排障手册见 [docs/deployment/troubleshooting.md](deployment/troubleshooting.md)。

排障文档只记录能体现工程判断、系统性定位和生产化经验的问题，不记录低价值操作失误。

## 推荐排查顺序

```text
容器状态
-> app 日志
-> worker 日志
-> db / redis 日志
-> Nginx 日志
-> 环境变量
-> 数据库迁移
-> 模型服务和 embedding provider
```

## 适合沉淀的问题

- VPS 上 GitHub fetch/clone TLS 超时，影响增量部署。
- Docker daemon 权限导致 compose 无法访问 Docker socket。
- PostgreSQL 生产迁移字段缺失，导致代码访问新字段时报错。
- Nginx 502/504 与后端未就绪、后端慢请求、LLM 超时的区别。
- DashScope embedding 额度耗尽后切换智谱 embedding-3。
- 新旧前端入口混淆导致访问旧 HTML 页面。

## 不写入公开排障文档的问题

- 纯粘贴命令导致终端显示不全。
- 临时记错路径、少打参数、重复点击按钮。
- 只和个人账号或平台控制台习惯有关的问题。
- 不能抽象成工程经验的问题。

## 统一排障格式

```text
问题现象：
影响范围：
定位过程：
根因：
修复方式：
沉淀经验：
```

“沉淀经验”要落到可迁移能力，例如如何区分前端错误、Nginx 代理错误和后端慢请求；为什么生产数据库迁移必须和代码版本同步；为什么 embedding provider 切换后需要重新入库或做模型隔离。
