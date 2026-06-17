# Vue3 管理员后台 V1：账号管理与 AI 可观测后台设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段的 Vue3 管理员后台建设。

当前 Vue3 前端已经有 `/vue/app/admin` 路由，但页面仍是占位内容：

```text
管理员后台
Vue3 V1 先保留后台入口，完整管理能力在 V2/V3 迁移。
```

这导致两个问题：

- 普通演示账号和管理员账号登录后的体验差异不明显。
- 项目已经有后端管理员接口，但 Vue3 新前端没有把这些能力产品化展示出来。

本阶段目标不是做一个复杂的企业级 RBAC 后台，而是先做一个可讲、可测、可演示的管理员后台 V1：

```text
账号管理基础能力
+ AI 应用可观测能力
+ 前后端权限边界
+ Vue3 后台页面体验
```

面试表达目标：

```text
我给系统补了管理员后台。前端根据当前用户 role 控制后台入口和页面访问体验，但真正的安全边界在后端 /api/admin/* 接口，所有后台接口都通过 require_admin_user 做权限校验。后台第一版聚焦低风险能力，包括用户列表、平台统计、RAG 质量诊断和 Agent 决策日志，用来观察系统运行情况，避免 AI 应用成为黑箱。
```

## 2. 当前基础

### 2.1 后端已经具备的能力

后端已经存在：

```text
User.role
require_admin_user
/api/admin/summary
/api/admin/config
/api/admin/users
/api/admin/rag/documents
/api/admin/rag/logs
/api/admin/rag/quality
/api/admin/agent/logs
```

对应证据：

```text
backend_python/db_models.py
backend_python/auth.py
backend_python/routes/admin.py
tests/test_admin_auth.py
tests/test_admin_routes.py
tests/test_admin_rag_quality.py
```

后端权限边界：

```text
未登录用户 -> 401
普通用户 -> 403
管理员 -> 放行
```

### 2.2 Vue3 前端当前状态

Vue3 前端已经具备：

```text
frontend/src/router/index.ts
frontend/src/stores/auth.ts
frontend/src/api/auth.ts
frontend/src/layouts/AppLayout.vue
frontend/src/pages/app/AdminPage.vue
```

当前问题：

- `AdminPage.vue` 只是占位页面。
- 侧边栏对普通用户和管理员没有明显区分。
- 没有 Vue3 版 admin API client。
- 没有 Vue3 版后台数据 store。
- 没有 Vue3 版后台统计、用户列表、RAG 质量、Agent 日志页面。
- 普通用户访问 `/vue/app/admin` 时缺少明确权限提示。

## 3. 设计结论

本阶段采用组合方案：

```text
A. 只读观察后台
+ B. 轻量账号管理
+ C. AI 工程可观测后台
```

优先级：

```text
先让管理员账号和普通账号明显不同
-> 再接回已有 /api/admin/* 只读接口
-> 再做用户筛选和 AI 质量诊断展示
-> 最后评估是否进入写操作后台
```

本阶段推荐先做低风险版本：

- 用户列表。
- 用户搜索。
- 角色筛选。
- 用户核心数据展示。
- 平台统计。
- RAG 质量诊断。
- Agent 决策日志。
- 系统配置只读展示。

本阶段暂不做：

- 删除用户。
- 禁用用户。
- 重置密码。
- 修改用户角色。
- 踢人下线。
- 复杂 RBAC。
- 操作审计日志。

原因：

```text
这些写操作会影响真实用户数据，需要额外设计审计日志、自我保护、最后一个管理员保护、误操作确认和回滚策略。为了保证当前阶段质量，先把只读后台和权限边界做扎实。
```

后续如果用户明确需要“真正能改账号”的后台，再写独立 spec：

```text
管理员后台 V2：账号写操作、审计日志与风控保护
```

## 4. 用户角色与路由权限

### 4.1 用户角色

当前只需要两类角色：

```text
user：普通用户
admin：管理员
```

不引入复杂 RBAC。

### 4.2 前端入口控制

`AppLayout.vue` 需要根据当前用户 role 控制后台入口：

```text
普通用户：不显示“后台”入口，或显示但进入后提示无权限。
管理员：显示“后台”入口。
```

推荐实现：

```text
普通用户不显示后台入口。
如果普通用户手动输入 /vue/app/admin，则显示权限提示页。
```

原因：

- 普通用户不被无关入口干扰。
- 手动访问时有明确反馈。
- 前端体验和后端权限同时存在。

### 4.3 后端权限边界

必须明确：

```text
前端隐藏按钮不是安全边界。
真正安全边界是后端 require_admin_user。
```

所有 `/api/admin/*` 调用都必须依赖后端 401 / 403。

前端需要把错误翻译为用户能理解的提示：

```text
401：登录状态已失效，请重新登录。
403：当前账号没有管理员权限。
```

## 5. 页面信息架构

### 5.1 后台首页

后台首页展示平台级概览：

```text
用户数
面试记录数
RAG 文档数
RAG 命中日志数
Agent 决策日志数
```

数据来源：

```text
GET /api/admin/summary
```

页面目的：

```text
让管理员一眼知道系统当前运行规模。
```

### 5.2 账号管理

账号管理 V1 先做只读和筛选。

字段：

```text
用户 ID
邮箱
用户名
角色
注册时间
```

数据来源：

```text
GET /api/admin/users
```

交互：

```text
按邮箱或用户名搜索
按角色筛选：全部 / 普通用户 / 管理员
显示当前筛选结果数量
```

暂不做：

```text
改角色
禁用账号
重置密码
删除用户
```

页面文案要避免误导，不使用“封禁”“删除”等按钮占位。

### 5.3 RAG 质量诊断

RAG 质量诊断是本项目的 AI 工程化亮点。

数据来源：

```text
GET /api/admin/rag/quality
```

展示内容：

```text
低质量召回总数
空召回数量
弱召回数量
未进入 prompt 数量
低质量召回样例
每条样例的 query_text、retriever_name、hit_count、issueType、recommendation
```

页面目的：

```text
让管理员能定位 RAG 为什么没查到、查弱了、或者查到了但没进入 prompt。
```

### 5.4 RAG 文档概览

数据来源：

```text
GET /api/admin/rag/documents
```

展示字段：

```text
标题
知识库类型
状态
可见性
chunk 数
重复 chunk 数
所属用户邮箱
更新时间
```

页面目的：

```text
观察知识库资料是否过少、是否被停用、是否存在重复内容。
```

V1 只读，不做跨用户删除文档。

### 5.5 Agent 决策日志

数据来源：

```text
GET /api/admin/agent/logs
```

展示字段：

```text
nextAction
stage
difficulty
focus
reason
fallbackUsed
createdAt
```

可读性增强：

```text
fallbackUsed=true 使用醒目标识
nextAction 使用中文标签辅助理解
reason 长文本折叠或限制行数
```

页面目的：

```text
观察 Agent 是否频繁 fallback、是否一直深挖同一话题、是否能根据回答状态切换策略。
```

### 5.6 系统配置只读

数据来源：

```text
GET /api/admin/config
```

展示内容：

```text
LLM 模型
Embedding 模型
Rerank 模型
数据库 URL 摘要
```

安全要求：

```text
不展示 API Key。
不展示完整敏感连接串。
```

如果后端当前返回的 `databaseUrl` 含敏感信息，前端需要只展示脱敏摘要，后续可考虑让后端直接返回 `databaseLabel`。

## 6. 前端架构设计

建议新增：

```text
frontend/src/api/admin.ts
frontend/src/stores/admin.ts
frontend/src/pages/app/AdminPage.vue
frontend/src/pages/app/admin-page.test.ts
```

### 6.1 admin API client

`frontend/src/api/admin.ts` 负责封装：

```text
fetchAdminSummary()
fetchAdminUsers()
fetchAdminRagDocuments()
fetchAdminRagQuality()
fetchAdminAgentLogs()
fetchAdminConfig()
```

只负责请求，不负责页面状态。

### 6.2 admin store

`frontend/src/stores/admin.ts` 负责：

```text
summary
users
ragDocuments
ragQuality
agentLogs
config
loading
error
loadDashboard()
```

推荐第一版用一个 `loadDashboard()` 并发加载后台首页数据。

错误处理：

```text
403 -> error = "当前账号没有管理员权限"
其他错误 -> error = 后端错误信息或通用提示
```

### 6.3 AdminPage

`AdminPage.vue` 负责页面编排：

```text
权限提示
统计卡片
账号管理表格
RAG 质量诊断
RAG 文档概览
Agent 决策日志
系统配置
```

不要把请求逻辑全塞在页面组件里。

页面应保持极简、克制、工具型：

- 信息密度适中。
- 卡片用于统计和列表容器。
- 不做营销式大标题。
- 不做过重后台模板。
- 移动端表格可以横向滚动或改成列表卡片。

## 7. 后端设计

本阶段优先不新增后端写接口。

如果现有 admin 接口已经满足页面展示，后端只做必要补齐：

- 确认 `/api/admin/users` 返回 `role`。
- 确认 `/api/admin/rag/quality` 返回 `summary` 和 `items`。
- 确认所有 `/api/admin/*` 普通用户访问为 403。
- 确认所有接口不泄露 API key。

如需补字段，优先补只读字段，不引入写操作。

## 8. 测试策略

### 8.1 后端测试

如后端接口不变，复用已有测试：

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_admin_rag_quality.py -q
```

如果补字段，需要新增或更新：

```text
普通用户访问 admin 接口返回 403
管理员可以访问 summary/users/rag/quality/agent logs/config
config 不返回 API key
```

### 8.2 Vue3 前端测试

需要新增或更新 Vitest：

```text
普通用户不显示后台入口
管理员显示后台入口
普通用户访问 AdminPage 显示无权限提示
管理员 AdminPage 会调用 admin store
统计卡片能渲染
用户列表能按邮箱/用户名搜索
用户列表能按 role 筛选
RAG 质量诊断能渲染 issueType 和 recommendation
Agent 日志能渲染 fallbackUsed
```

建议命令：

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

### 8.3 浏览器验证

需要验证：

```text
普通用户登录：不显示后台入口，手动访问 /vue/app/admin 有权限提示
管理员登录：显示后台入口，可以看到统计、用户、RAG 质量、Agent 日志
登出后不能访问后台
移动端后台页面不出现横向溢出或文字挤压
页面不出现 undefined
```

## 9. 追求目标执行边界

为了减少追求目标任务中途频繁确认，本阶段 spec 明确允许以下动作自动执行：

```text
读取项目文件
修改 frontend/src 下的 Vue3 前端文件
必要时修改 backend_python/routes/admin.py 的只读返回字段
新增或更新前后端测试
运行 npm.cmd run test
运行 npm.cmd run build
运行 python -m pytest -q
启动本地开发服务器用于浏览器验证
使用内置浏览器访问 localhost / 127.0.0.1 做验证
更新本 spec 对应的 plan 和学习文档
```

以下动作不应自动执行，除非用户再次明确确认：

```text
删除真实用户数据
删除数据库文件
新增删除用户、禁用用户、重置密码等写操作
修改线上部署配置
推送 GitHub
创建 Pull Request
安装新的重型依赖
访问外部网站并提交表单
发送 API Key、密码、token 等敏感信息
执行破坏性 git 操作
```

说明：

```text
完全访问模式可以减少文件系统和命令权限阻碍，但 Codex App 对某些高风险动作仍可能弹确认。spec 可以把允许范围写清楚，减少模型主动询问；但不能绕过应用自身的安全确认机制。
```

## 10. 验收标准

本阶段完成时应满足：

- 管理员账号和普通账号登录后体验有明显区别。
- 普通用户默认看不到后台入口。
- 普通用户手动访问后台有明确无权限提示。
- 管理员可以进入 Vue3 后台页面。
- Vue3 后台展示平台统计。
- Vue3 后台展示用户列表、搜索和角色筛选。
- Vue3 后台展示 RAG 质量诊断。
- Vue3 后台展示 Agent 决策日志。
- Vue3 后台展示系统配置只读信息。
- 不新增高风险账号写操作。
- 不破坏现有 `/api/admin/*` 权限边界。
- 前端测试通过。
- 前端 build 通过。
- 后端 admin 相关测试通过。
- 必要时全量 pytest 通过。

## 11. 分阶段实施建议

### 阶段 1：权限入口和页面骨架

- `AppLayout` 根据 user.role 控制后台入口。
- `AdminPage` 区分普通用户和管理员。
- 补对应 Vitest。

### 阶段 2：admin API client 和 store

- 新增 admin API client。
- 新增 admin store。
- 接入 summary/users/rag quality/agent logs/config。
- 补 store 测试。

### 阶段 3：账号管理 V1

- 用户列表。
- 搜索。
- role 筛选。
- 无数据和 loading/error 状态。

### 阶段 4：AI 可观测后台

- RAG 质量诊断面板。
- RAG 文档概览。
- Agent 决策日志。
- 系统配置只读。

### 阶段 5：验证和学习文档

- 跑前端测试。
- 跑前端 build。
- 跑后端 admin 测试。
- 浏览器验证普通用户和管理员路径。
- 新增学习文档：

```text
docs/learning/13-Vue3管理员后台如何承接权限和AI可观测性.md
```

## 12. 后续扩展

后续可以单独写 spec：

```text
管理员后台 V2：账号写操作、审计日志与风控保护
```

可能包含：

- 修改用户角色。
- 禁用 / 启用账号。
- 重置密码。
- refresh token 撤销。
- 操作审计日志。
- 最后一个管理员保护。
- 管理员不能禁用自己。

也可以单独写 spec：

```text
AI Ops Console V2：Agent / RAG 调试台与 LangGraph human-in-the-loop
```

可能包含：

- Agent 决策路径详情页。
- LangGraph checkpoint 查看。
- human-in-the-loop interrupt / resume。
- 高风险报告人工审核。

这些都不进入本阶段，避免范围膨胀。

