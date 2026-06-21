# 文档入口

这个目录保存 AI 模拟面试系统开发过程中的路线、spec、plan、学习资料、部署资料和项目讲解资料。

为了避免被旧文档带偏，继续开发时请按下面顺序阅读。

## 1. 当前路线

优先看：

```text
docs/PROJECT_STATUS.md
docs/roadmap/current-state.md
```

`docs/PROJECT_STATUS.md` 是公开短入口，`docs/roadmap/current-state.md` 是当前唯一可信的完整项目状态入口，负责回答：

- 现在真实落地了什么。
- 哪些内容已经完成，不要重复开发。
- 哪些内容只是历史规划。
- 下一阶段更适合做什么。

如果它和旧 spec、旧 plan 冲突，以 `current-state.md` 为准。

## 2. 项目基线

```text
docs/project-baseline.md
```

用于快速理解项目定位、核心链路、目录结构、本地启动、部署形态和当前边界。

## 3. 部署资料

```text
docs/DEPLOYMENT.md
docs/deployment/
```

推荐阅读：

1. `docs/DEPLOYMENT.md`
2. `vps-deploy-v1.md`
3. `troubleshooting.md`
4. `backup-and-rollback.md`
5. `nginx-cloudflare-https.md`

当前项目已经完成 IP + 8080 端口公网演示，后续域名和 HTTPS 可以继续参考这些文档。

## 4. 演示资料

```text
docs/demo/public-demo-materials.md
```

这里放虚构简历、虚构岗位 JD、公司信息和完整链路演示步骤。公网测试时优先使用这些资料，不要上传自己的真实隐私信息。

## 5. 学习资料

```text
docs/learning/
```

推荐顺序：

1. `00-学习总览.md`
2. `01-项目总讲解.md`
3. `02-FastAPI后端.md`
4. `03-RAG工程化.md`
5. `04-Agent工程化.md`
6. `05-部署与中间件.md`
7. `08-LangGraph如何承接自研Agent.md`

## 6. 项目讲解和简历材料

```text
docs/project-explanation/
```

重点文件：

- `ai-interview-system-overview.md`
- `data-model.md`
- `project-demo-script.md`
- `interview-deep-dive-qa.md`
- `resume-bullets-python-backend.md`
- `resume-bullets-ai-application.md`

注意：公开仓库里的 `resume-bullets-*` 是历史项目讲解材料。BOSS 项目描述、附件简历 bullet、面试讲解稿和求职策略应放在仓库外私有目录，不提交 GitHub。

## 7. 排障复盘

```text
docs/TROUBLESHOOTING.md
docs/deployment/troubleshooting.md
```

排障文档只沉淀能体现工程判断的问题，例如生产数据库迁移、Nginx 502/504、embedding provider 切换、Docker 权限和 VPS GitHub 拉取超时。不记录纯粘贴、路径记错等低价值操作问题。

## 8. Spec 和 Plan

已经完成的历史文档：

```text
docs/specs/completed/
docs/plans/completed/
```

真正待执行的新文档应该放在：

```text
docs/specs/active/
docs/plans/active/
```

如果 `active/` 为空，说明下一阶段还需要先讨论并写新 spec，不要从 `completed/` 里挑旧文档重复执行。
