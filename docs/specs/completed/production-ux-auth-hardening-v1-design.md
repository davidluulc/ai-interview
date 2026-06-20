# Production UX & Auth Hardening V1 设计文档

更新时间：2026-06-20

## 1. 阶段定位

本阶段用于把公网演示后的几个“能跑但不够像产品”的问题系统性收口，同时补上一个有生产化价值的安全能力：Redis 会话控制与管理员踢人下线。

当前项目已经完成：

- FastAPI + Vue3 + PostgreSQL + Redis + Celery + Nginx 的公网部署。
- 用户注册、登录、access token、refresh token、退出登录和基础管理员权限。
- 面试、RAG、LangGraph、报告、训练任务、管理员后台和 AI 调试台。
- 公网环境已经能完成一次面试、生成报告、保存历史并生成训练任务。

因此本阶段不是继续堆新业务模块，而是围绕“演示可理解、后台可诊断、安全可控制”做一轮硬化。

阶段名称：

```text
Production UX & Auth Hardening V1
```

## 2. 当前暴露的问题

### 2.1 报告页解释信息偏调试化

报告页中的“为什么这样问”本意是解释出题依据，但现在存在两个问题：

- 文案偏内部调试，比如直接展示 RAG 命中来源、关键词、弱召回等。
- 低质量 fallback 内容也会展示成一个大板块，看起来像废话或错误解释。

用户需要的是“这道题为什么和我的简历、JD、历史回答有关”，不是完整调试日志。

### 2.2 训练页薄弱点地图和任务列表关系不清

训练页左侧有“薄弱点训练地图”，右侧又有完整训练任务列表。当前交互容易让人困惑：

- 不点击左侧薄弱点时，右侧展示全部任务。
- 点击左侧薄弱点后，右侧像是被筛选，但页面没有明确告诉用户当前处于筛选状态。
- 左侧地图更像任务入口，但右侧任务列表又重复承担入口职责。

这会让用户不知道应该点左边还是看右边。

### 2.3 管理员 AI 调试台信息堆叠

后台 AI 调试控制台已经能展示最近 AI 请求、RAG 质量诊断、Agent 决策日志等信息，但现在像把所有内部日志直接摊在一页：

- 最近请求列表、RAG 链路、Agent 决策、诊断建议缺少分类。
- RAG 召回链路和诊断建议重复多次。
- `good`、`weak` 等标签没有产品化中文解释。
- 单次请求的“摘要”和“细节”边界不清。

管理员需要的是快速定位问题，而不是阅读原始日志堆。

### 2.4 Redis 鉴权会话控制尚未生产化

当前项目已经有双 token 基础：

- access token 用于接口访问。
- refresh token 存储在数据库 `refresh_tokens` 中。
- 退出登录会撤销 refresh token。
- 当前 access token 会加入 token blacklist。

但当前 token blacklist 是内存实现，缺少生产环境下跨进程、重启后仍有效的会话控制能力。管理员也无法主动把某个用户踢下线。

本阶段要把 Redis 从“健康检查/队列基础设施”进一步用到真实生产鉴权场景。

## 3. 总体目标

完成后，项目应达到以下状态：

```text
报告页：用户能理解每道题为什么被问，低质量解释不再硬展示。
训练页：薄弱点地图是明确的筛选器，任务列表状态清楚。
后台页：AI 调试台按请求、RAG、Agent、诊断分层展示，重复信息被聚合。
鉴权：管理员可以让用户会话失效，Redis 支撑 access token 即时撤销和会话状态检查。
```

这个阶段的简历价值是：

```text
在 AI 模拟面试系统上线后，针对公网演示中暴露的复盘解释、训练任务交互、AI 可观测性和会话安全问题做生产化收口；引入 Redis 会话控制，实现 JWT 双 token + Redis session 的强制下线能力，并对 RAG/Agent 调试信息做聚合和产品化展示。
```

## 4. 范围

### 4.1 要做

1. 报告页“出题依据”收口
   - 将“为什么这样问”改成“出题依据”。
   - 展示 2-3 条用户能理解的理由。
   - 合并重复 RAG reason。
   - 如果只有低质量 fallback 文案，则隐藏该板块或展示轻量空状态。

2. 训练页薄弱点筛选收口
   - 左侧薄弱点地图定位为筛选器和概览。
   - 默认展示全部任务。
   - 点击某个薄弱点后，右侧只展示对应任务。
   - 右侧标题、数量和空状态明确显示当前筛选条件。
   - 提供“查看全部/清除筛选”。

3. 后台 AI 调试台分类与去重
   - 将 AI 调试台拆成清晰区域或 tabs：
     - 最近请求
     - RAG 召回
     - Agent 决策
     - 诊断建议
   - 默认展示摘要，展开后看细节。
   - 对 RAG 链路按 `knowledgeBase + quality + suggestion` 聚合。
   - 将 `good / weak / empty` 转成中文质量标签。
   - 重复诊断建议显示为“出现 N 次”，不重复刷屏。

4. Redis 会话控制
   - access token 增加可追踪的 session 标识。
   - 登录后在 Redis 中写入 session 状态。
   - refresh token 继续保留数据库持久化，作为长期登录凭据。
   - 鉴权依赖检查 Redis session 是否有效。
   - 退出登录时撤销 refresh token，并删除/撤销 Redis session。
   - 管理员后台支持对用户执行“强制下线”。
   - 前端遇到 `session_revoked` 或 `token_revoked` 时清理 token 并跳转登录页。

5. 测试与部署
   - 后端覆盖 session 创建、刷新、退出、管理员踢人、被踢后访问失败。
   - 前端覆盖训练筛选、报告出题依据、管理员调试台聚合、被踢下线提示。
   - Docker/VPS 环境验证 Redis session 生效。

### 4.2 不做

本阶段不做以下内容：

- 不重做全站 UI。
- 不重写 RAG 检索算法。
- 不重做数据库表关系。
- 不引入新的权限系统或复杂 RBAC。
- 不做短信、邮箱、OAuth 第三方登录。
- 不做多设备管理完整页面，只做管理员强制下线的最小闭环。
- 不把所有 AI 调试原始日志长期归档成审计系统。

## 5. 数据和架构设计

### 5.1 是否需要重新规划数据库表关系

本阶段不需要重做数据库表关系。

原因：

- 报告页、训练页、AI 调试台的问题主要是展示层、归一化和去重问题。
- RAG 日志和 Agent 日志已经存在，只需要在 API 或前端做聚合视图。
- refresh token 已经有 `refresh_tokens` 表，不需要新增一整套 session 表。

Redis 会话控制可以先采用“数据库 refresh token + Redis session 状态”的组合：

```text
PostgreSQL refresh_tokens:
长期凭据、过期时间、revoked_at、用户关联

Redis session:
短期在线状态、是否被踢、最近活跃时间、access token 所属 session
```

### 5.2 Redis key 设计

建议使用以下 key：

```text
auth:session:{session_id}
auth:user_sessions:{user_id}
auth:revoked_access:{access_token_hash}
```

`auth:session:{session_id}` 保存：

```json
{
  "userId": 1,
  "refreshTokenId": 10,
  "status": "active",
  "createdAt": "2026-06-20T00:00:00Z",
  "lastSeenAt": "2026-06-20T00:10:00Z",
  "revokedReason": ""
}
```

`auth:user_sessions:{user_id}` 用于管理员按用户踢下线时快速找到该用户的 session。

`auth:revoked_access:{access_token_hash}` 用于保存短期 access token 黑名单，TTL 与 access token 剩余有效期一致。

### 5.3 双 token + Redis session 流程

登录：

```text
校验账号密码
-> 创建 refresh_token 数据库记录
-> 生成 session_id
-> 写入 Redis auth:session:{session_id}
-> access token 写入 user_id + session_id + type=access
-> refresh token 返回前端
```

鉴权：

```text
解析 access token
-> 检查 access token blacklist
-> 读取 session_id
-> 检查 Redis session 是否存在且 status=active
-> 读取用户并继续请求
```

刷新：

```text
校验 refresh token 数据库记录未过期、未撤销
-> 检查对应 session 仍 active
-> 签发新的 access token
```

退出登录：

```text
撤销 refresh token
-> 删除或标记 Redis session revoked
-> 当前 access token 加入 Redis blacklist
```

管理员踢人：

```text
管理员选择用户
-> 查 auth:user_sessions:{user_id}
-> 将该用户所有 session 标记 revoked
-> 数据库中该用户 refresh_tokens.revoked_at 批量写入
-> 返回踢下线数量
```

前端处理：

```text
任意接口返回 401 且 code=session_revoked/token_revoked
-> 清空 accessToken/refreshToken
-> 跳转 /vue/auth/login
-> 展示“账号已在后台被管理员下线，请重新登录”
```

## 6. 页面设计

### 6.1 报告页

把“为什么这样问”改为“出题依据”。

展示规则：

- 有高质量 `decisionSummary` 时展示一段摘要。
- 有 `ragReasons` 时最多展示 3 条，按来源去重。
- 候选人画像、题库、岗位知识库命中内容要转成人话。
- 如果只有“本题由当前档案、历史回答和检索上下文共同驱动”这类 fallback，则不展示大板块。

示例：

```text
出题依据
这轮主要围绕 RAG 链路理解展开，因为你的 JD 提到需要掌握检索增强生成，上一轮回答中又缺少日志字段和质量排查细节。

- 岗位知识库命中：RAG Agent 与 LangGraph 项目知识
- 题库命中：PostgreSQL、Redis、Celery 生产化职责
- 候选人画像命中：Python 后端开发实习生
```

### 6.2 训练页

左侧“薄弱点训练地图”作为筛选器：

```text
薄弱点训练地图
全部
RAG 日志字段
FastAPI 后端模块
数据库建模
```

右侧标题随筛选变化：

```text
训练任务 · 全部（6 个）
训练任务 · RAG 日志字段（2 个）
```

空状态：

```text
当前薄弱点暂无训练任务。你可以从最近一份面试报告生成专项训练。
```

### 6.3 管理员 AI 调试台

调试台保留“最近 AI 请求”列表，但右侧详情拆成 tabs：

```text
总览 | RAG 召回 | Agent 决策 | 诊断建议 | 原始日志
```

默认打开“总览”，只展示：

- 请求类型
- 模型状态
- RAG 总命中
- 质量标签
- Agent 动作
- 是否 fallback

“RAG 召回”按知识库聚合：

```text
候选人画像：命中 1 条，高相关
题库：命中 4 条，高相关
岗位知识库：命中 4 条，弱相关
```

“诊断建议”按标题和正文去重：

```text
岗位知识库弱召回
岗位知识库召回质量偏弱，建议补充题库样例、优化 chunk 标题或调整检索关键词。
出现 6 次
```

质量标签中文化：

```text
good -> 高相关
weak -> 弱相关
empty -> 空召回
unknown -> 未评估
```

## 7. API 设计

### 7.1 Auth

新增或增强：

```text
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
POST /api/admin/users/{user_id}/force-logout
```

`POST /api/admin/users/{user_id}/force-logout` 返回：

```json
{
  "ok": true,
  "revokedSessions": 2,
  "revokedRefreshTokens": 2
}
```

401 错误建议结构：

```json
{
  "detail": {
    "code": "session_revoked",
    "message": "当前登录会话已失效，请重新登录。"
  }
}
```

### 7.2 Admin debug

优先在现有 API 上做聚合字段，不强行新增复杂接口。

建议增加聚合结果：

```json
{
  "ragSummary": [
    {
      "knowledgeBase": "role_knowledge",
      "label": "岗位知识库",
      "hitCount": 4,
      "quality": "weak",
      "qualityLabel": "弱相关"
    }
  ],
  "diagnosticSummary": [
    {
      "title": "岗位知识库弱召回",
      "message": "岗位知识库召回质量偏弱，建议补充题库样例、优化 chunk 标题或调整检索关键词。",
      "count": 6
    }
  ]
}
```

## 8. 验收标准

### 8.1 报告页

- “为什么这样问”不再作为标题出现。
- 新标题为“出题依据”。
- fallback 解释不会占据大块页面。
- RAG reasons 去重后最多展示 3 条。
- 用户能看懂问题来自简历、JD、历史回答还是知识库。

### 8.2 训练页

- 默认显示全部任务。
- 点击薄弱点后只显示该薄弱点任务。
- 页面明确显示当前筛选条件和任务数量。
- 可以一键恢复查看全部。

### 8.3 管理员 AI 调试台

- 最近请求列表和详情区域分离。
- RAG、Agent、诊断建议有清晰分类。
- RAG 质量标签中文化。
- 重复诊断建议被聚合，不重复刷屏。
- 原始日志仍可查看，但默认不展开。

### 8.4 Redis 会话控制

- 登录后 Redis 中存在 session。
- access token 中包含 session 标识。
- Redis session 被撤销后，旧 access token 不能继续访问 `/api/auth/me`。
- refresh token 被撤销后不能刷新 access token。
- 管理员可以强制某个用户下线。
- 被踢用户前端自动清 token 并跳转登录页。
- Redis 不可用时，本地测试模式可降级，但生产模式要暴露清晰健康状态。

## 9. 测试策略

后端：

```bash
python -m pytest tests/test_auth.py -q
python -m pytest tests/test_admin_users.py -q
python -m pytest tests/test_admin_ai_debug.py -q
python -m pytest tests/test_training_tasks.py -q
python -m pytest tests/test_question_reviews.py -q
python -m pytest -q
```

前端：

```bash
cd frontend
npm.cmd run test -- src/pages/app/report-page.test.ts
npm.cmd run test -- src/pages/app/training-page.test.ts
npm.cmd run test -- src/pages/app/admin-page.test.ts
npm.cmd run test -- src/api/client.test.ts
npm.cmd run test
npm.cmd run build
```

部署验证：

```bash
curl http://127.0.0.1:8080/api/health
sudo docker compose --env-file .env.production ps
```

并在公网手动验证：

```text
登录
完成一轮面试
查看报告出题依据
进入训练页筛选 weakTag
管理员后台查看 AI 调试聚合
管理员强制下线测试账号
测试账号刷新页面后回到登录页
```

## 10. 推荐实施顺序

1. 报告页出题依据收口
   - 风险低，立刻改善用户观感。

2. 训练页筛选交互收口
   - 风险低，能改善训练闭环理解。

3. 管理员 AI 调试台分类和去重
   - 中等风险，涉及数据聚合和前端布局。

4. Redis 会话控制和强制下线
   - 风险最高，涉及鉴权链路，必须 TDD 和充分回归。

5. 公网部署和演示验证
   - 更新服务器后，跑一遍完整链路。

## 11. 非目标提醒

如果开发中出现以下想法，应延后到下一阶段：

- 给用户做完整多设备管理页。
- 做更复杂的组织/租户权限。
- 改造全部日志表结构。
- 大规模重做管理员后台信息架构。
- 为 RAG 引入新的数据库或搜索引擎。

本阶段的边界是：先把已经上线的功能讲清楚、用顺手、管得住。
