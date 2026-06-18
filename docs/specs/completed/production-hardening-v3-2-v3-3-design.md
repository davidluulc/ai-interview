# Production Hardening V3.2 + V3.3：安全、流量保护、幂等与可观测性增强

更新时间：2026-06-17

## 1. 背景

当前项目已经完成以下生产化前置阶段：

- Backend Production Infrastructure V1：补齐 SQLite/PostgreSQL 配置兼容、Redis 健康检查、Celery eager/health task 和基础设施观测。
- Async RAG Ingestion V2：RAG 文档上传和 retry 已迁移为 `RagIngestionTask` 持久化任务，并通过 Celery taskId 派发。
- Production Hardening V3.1：Celery worker mode 可观测，RAG ingestion dispatch 能区分 eager 完成、worker queued 和 dispatch failed，并记录 dispatch/timing metadata。

下一阶段不应重复做 V3.1，也不应直接跳到 Docker/Nginx/VPS/HTTPS 上线。本阶段要处理上线前后端系统更容易被问到的工程化问题：登录态失效、接口防刷、敏感错误脱敏、重复提交、任务幂等、retry 并发保护和管理员可观测性。

## 2. 阶段定位

本阶段是 Production Hardening 的第二个可执行阶段，合并执行 V3.2 和 V3.3：

```text
V3.2 安全与流量保护
-> V3.3 缓存、幂等和可观测性增强
```

合并的原因是：token blacklist、rate limit、idempotency、retry lock 和任务异常聚合都需要复用 Redis/本地 fallback 能力。分开开发会让底座重复设计，合并规划能让接口边界和测试策略更清晰。

## 3. 本阶段目标

完成后，系统应具备：

- 退出登录后 refresh token 继续保持数据库撤销，同时可选把 access token 加入 blacklist。
- Redis 不可用时仍能本地测试，不要求真实 Redis 才能跑完整测试。
- 登录、RAG 文件上传、RAG retry、AI 面试生成等高风险接口具备基础限流。
- 后端未处理异常、模型供应商错误、embedding/rerank 错误等对前端返回稳定、脱敏的错误信息。
- RAG ingestion upload 支持防重复提交，避免短时间内同一用户、同一文件、同一知识库重复创建任务。
- RAG ingestion retry 支持轻量锁或状态保护，避免同一个失败任务被并发重复 retry。
- 管理员后台可以看到安全/限流/幂等相关配置摘要和任务异常聚合信息。

## 4. 严格边界

本阶段不做：

- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不强制安装 PostgreSQL，不迁移默认本地数据库，SQLite 仍是本地默认。
- 不强制启动真实 Redis；Redis 能力必须有 disabled/fallback/test path。
- 不引入 Qdrant、pgvector、对象存储。
- 不做 OCR、Word / Excel / 网页解析。
- 不重构 RAG 检索、hybrid search、rerank、evaluation 算法。
- 不重构 Agent、LangGraph 或 Vue3 主链路。
- 不做复杂 RBAC 权限矩阵、短信/邮箱验证码、找回密码或商业化账号体系。
- 前端只做最小展示和文案兼容，不做页面大重构。

## 5. V3.2：安全与流量保护

### 5.1 Token blacklist

当前 refresh token 已有撤销式退出登录。V3.2 继续保留这个数据库策略，并新增 access token blacklist 能力：

- 新增轻量 token blacklist service。
- 优先使用 Redis cache；Redis disabled 时使用进程内 fallback，保证测试可运行。
- blacklist key 使用 token jti 或 token hash，避免直接保存完整 token。
- access token 过期时间内命中 blacklist 时，`get_current_user` 应拒绝请求。
- `/api/auth/logout` 成功后把当前 access token 加入 blacklist，同时继续撤销 refresh token。
- `/api/admin/config` 或基础设施摘要中展示 blacklist backend：`redis` / `memory` / `disabled`。

不做内容：

- 不实现跨设备全部下线。
- 不实现 refresh token 家族轮换。
- 不实现复杂会话管理后台。

### 5.2 Rate limit

新增基础限流能力，保护高风险接口：

- 登录接口：防止暴力尝试。
- RAG 文件上传接口：防止频繁上传大文件。
- RAG retry 接口：防止重复触发失败任务。
- AI 生成接口：保护 `/api/interview/next-question` 和报告生成相关路径。

设计要求：

- 提供 `RateLimiter` 抽象，支持 Redis backend 和 memory fallback。
- key 维度至少包含 IP、用户 id 或接口分组。
- 被限流时返回 `429`，响应体使用项目统一错误格式。
- 响应头可以包含 `Retry-After` 或最小限流摘要。
- 测试不能依赖真实 Redis。

建议初始策略：

```text
auth.login: 5 次 / 分钟 / IP
rag.upload: 10 次 / 分钟 / user
rag.retry: 6 次 / 分钟 / user
interview.next_question: 30 次 / 分钟 / user
report.generate: 10 次 / 分钟 / user
```

这些值是开发默认值，允许通过环境变量覆盖。

### 5.3 错误脱敏

当前部分 provider client 会把供应商响应体或异常文本拼到 `HTTPException.detail` 中。V3.2 要统一约束：

- 对外返回稳定错误码和简短中文/英文信息。
- 内部日志保留更详细的 provider status、attempt、duration、safe body 摘要。
- 不向前端暴露 API key、完整 URL、本地绝对路径、数据库连接串、栈追踪。
- 全局异常处理继续返回统一错误格式。

建议对外错误信息：

```text
LLM provider request failed.
Embedding provider request failed.
Rerank provider request failed.
External provider request timed out.
```

中文前端可显示为“外部模型服务暂时不可用，请稍后重试”。

### 5.4 管理员权限边界加固

继续保持“后端强鉴权”：

- 管理员接口必须依赖 `require_admin_user` 或等价后端依赖。
- 增加测试覆盖普通用户访问关键 admin 接口返回 403。
- 不依赖前端隐藏入口作为权限控制。
- 管理员后台显示安全配置摘要，但不展示敏感值。

## 6. V3.3：缓存、幂等和可观测性增强

### 6.1 RAG upload 防重复提交

问题：用户连续点击上传按钮或网络重试时，可能短时间内创建重复 ingestion task。

目标：

- 基于 `user_id + knowledge_base + file_hash + title` 生成 idempotency key。
- 在短时间窗口内，如果存在同样 key 的 pending/queued/running/succeeded task，优先返回已有 task。
- 如果已有任务 failed 且可 retry，不自动创建新任务，提示或返回该 failed task 供用户 retry。
- idempotency metadata 写入 `result_json` 或已有任务字段，暂不新增表，除非测试显示现有字段无法承载。

边界：

- 不做全局文件去重系统。
- 不做跨用户去重。
- 不阻止用户明确修改 title 或 metadata 后重新上传。

### 6.2 RAG retry 并发保护

问题：同一个失败 ingestion task 被多次点击 retry，可能重复派发 Celery task。

目标：

- retry 前检查任务当前状态，只允许 failed 且 canRetry 的任务进入 retry。
- retry 开始后立刻把任务状态切回 queued，并写入 `retryLockedAt` 或等价 result metadata。
- 如果任务已经 queued/running，则返回 409，提示任务正在处理。
- Redis 可用时可以使用短锁；Redis 不可用时必须依赖数据库状态检查保证本地测试稳定。

### 6.3 任务异常聚合

管理员后台需要从“看列表”升级到“能定位常见失败类型”：

- 后端聚合最近 ingestion task 的失败阶段：`dispatch` / `execute` / `parse` / `embedding` / `unknown`。
- 聚合最近失败原因 topN，做脱敏和截断。
- 展示平均耗时、最长耗时、失败数、可重试数、当前 queued/running 数。
- 不做 Prometheus/Grafana，不引入 APM。

### 6.4 缓存能力的最小落地

Redis cache 目前主要是健康检查入口。本阶段只做低风险缓存：

- admin dashboard summary 可加短 TTL cache。
- RAG quality summary 可加短 TTL cache。
- 缓存失效时必须回源，不影响功能正确性。
- 测试覆盖 Redis disabled fallback。

不缓存内容：

- 不缓存用户隐私简历全文。
- 不缓存完整 LLM prompt。
- 不缓存 access token 明文。

## 7. 接口兼容要求

必须保持兼容：

- `/api/auth/login`
- `/api/auth/logout`
- `/api/auth/refresh`
- `/api/interview/next-question`
- `/api/rag/documents/upload`
- `/api/rag/documents/ingestion-tasks`
- `/api/rag/documents/ingestion-tasks/{task_id}`
- `/api/rag/documents/ingestion-tasks/{task_id}/retry`
- `/api/admin/config`
- `/api/admin/rag/ingestion-tasks`
- `/api/health`

允许新增字段，不允许删除现有字段。

建议新增只读字段：

```text
security.rateLimit.enabled
security.rateLimit.backend
security.tokenBlacklist.backend
security.idempotency.enabled
security.idempotency.backend
security.errorRedaction.enabled
```

ingestion task 可新增：

```text
idempotencyKey
idempotencyHit
retryLockedAt
failureStage
durationMs
```

## 8. 前端最小改动

允许改动：

- Vue3 管理员后台系统配置区显示安全/限流/幂等摘要。
- Vue3 管理员后台 RAG ingestion 监控区显示失败阶段、平均耗时、最长耗时、幂等命中数。
- Vue3 知识库页 retry/upload 文案兼容 409/429。
- API type 增加可选字段。

不允许改动：

- 不做整体 UI 重构。
- 不重写 Pinia store 架构。
- 不改路由结构。
- 不引入新的前端框架。

## 9. 测试策略

后端优先测试驱动。

V3.2 测试建议：

- logout 后当前 access token 命中 blacklist 时访问受保护接口返回 401。
- Redis disabled 时 token blacklist 使用 memory fallback，测试可运行。
- 登录接口超过限制返回 429。
- RAG upload 超过限制返回 429。
- next-question 超过限制返回 429。
- 普通用户访问关键 admin 接口返回 403。
- provider client 对外错误不包含敏感响应体、API key、数据库 URL 或本地路径。

V3.3 测试建议：

- 同一用户短时间重复上传同一文件返回已有 ingestion task，不重复创建任务。
- 不同用户上传同一文件不会互相影响。
- failed 且 canRetry 的任务可以 retry。
- queued/running 的任务 retry 返回 409。
- dispatch failed / execute failed 能正确聚合到管理员摘要。
- admin config 返回安全/限流/幂等配置摘要且不泄漏敏感值。

前端测试建议：

- 管理员后台显示安全/限流/幂等摘要。
- 管理员后台显示 RAG ingestion 异常聚合。
- 知识库页遇到 409/429 时显示可理解提示。
- 页面文本不出现 `undefined`。

回归验证：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

桌面端和移动端都要确认：

- 无 `undefined`。
- 无横向溢出。
- 管理员后台能看到安全/限流/幂等摘要。
- 知识库页对 queued、409、429 的文案清晰。

## 10. 文档与归档要求

完成后必须更新：

- `docs/project-baseline.md`
- `docs/roadmap/current-state.md`
- `docs/specs/README.md`
- `docs/plans/README.md`

完成后将本 spec 和对应 plan 移到：

```text
docs/specs/completed/
docs/plans/completed/
```

如果只完成 V3.2，不能宣称 V3.3 完成；如果 V3.2/V3.3 都完成，才可以标记本阶段完成。

## 11. 面试表达种子

可以这样讲：

```text
我没有只停留在能跑通 RAG 和 Agent，而是继续做了上线前的后端生产化加固。比如登录退出后，我用 token blacklist 让 access token 在过期前也能失效；对登录、上传、AI 生成等高风险接口做基础限流；对模型供应商错误做脱敏，避免把内部响应和配置暴露给前端。同时，RAG 文档入库这类异步任务容易出现重复提交和重复 retry，所以我设计了幂等 key 和 retry 状态保护，让任务可靠性更接近真实生产环境。管理员后台可以看到安全配置、限流状态、任务失败阶段和异常聚合，这样出了问题能定位在登录、限流、任务投递、任务执行还是外部模型服务。
```

## 12. 追求目标建议文本

```text
根据 docs/specs/active/production-hardening-v3-2-v3-3-design.md，持续推进 AI 模拟面试系统 Production Hardening V3.2 + V3.3。

要求：
1. 先根据 active spec 编写 docs/plans/active/production-hardening-v3-2-v3-3.md，然后严格按 plan 执行。
2. 本阶段合并执行 V3.2 安全与流量保护、V3.3 缓存/幂等/可观测性增强。
3. 每轮开发前先用中文解释本轮要学的后端生产化、安全、限流、幂等或异步任务可靠性知识点。
4. 开发时优先测试驱动，先写或更新后端测试，再实现。
5. 保持 SQLite 作为本地默认开发数据库，不强制安装 PostgreSQL。
6. 保留 Redis disabled / memory fallback 测试能力，不要求本地真实启动 Redis 才能跑测试。
7. 允许增加 token blacklist、rate limiter、idempotency、retry lock、错误脱敏、安全配置摘要和任务异常聚合字段，但不能破坏现有接口兼容。
8. 不做 Docker、Nginx、VPS、HTTPS 上线。
9. 不引入 Qdrant、pgvector、对象存储。
10. 不做 OCR、Word / Excel / 网页解析。
11. 不重构 RAG 检索、hybrid search、rerank、evaluation 算法。
12. 不重构 Agent、LangGraph 或 Vue3 主链路。
13. 前端只允许最小化更新知识库页和管理员后台的安全/限流/幂等/任务异常展示兼容，不做页面大重构。
14. 完成后运行 python -m pytest -q、cd frontend && npm.cmd run test、cd frontend && npm.cmd run build。
15. 完成后使用内置浏览器验证 /vue/app/knowledge 和 /vue/app/admin 的桌面端与移动端，无 undefined、无横向溢出。
16. 完成后更新 docs/project-baseline.md、docs/roadmap/current-state.md、docs/specs/README.md、docs/plans/README.md。
17. 如果只完成 V3.2，只能标记 V3.2 完成；只有 V3.2 和 V3.3 都完成后，才能标记本阶段完成。
```
