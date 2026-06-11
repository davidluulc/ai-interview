# 13 管理员后台 MVP 如何设计

## 1. 为什么需要管理员后台

AI 模拟面试系统不是只有用户端。

当项目逐渐具备：

```text
用户系统
RAG 知识库
RAG 命中日志
Agent 决策日志
训练任务
历史面试记录
```

之后，就需要一个最小后台来观察系统运行情况。

后台 MVP 的目标不是一开始就做“大而全运营系统”，而是先回答几个基础问题：

```text
当前有多少用户？
知识库里有哪些文档？
RAG 最近查到了什么？
Agent 最近为什么做出某些决策？
系统模型配置大概是什么？
```

## 2. 为什么第一版只做只读后台

后台功能有两类：

```text
只读能力：查看用户、文档、日志、配置。
写入能力：删除文档、封禁用户、改配置、踢人下线。
```

第一版只做只读，是为了降低风险。

原因是：

- 只读列表能证明后台管理能力。
- 不会误删用户数据。
- 不会引入复杂 RBAC。
- 测试和权限边界更容易稳定。
- 更符合 MVP 逐步迭代思路。

后续如果要做删除、封禁、配置修改，应该单独写 spec 和测试。

## 3. 后端权限边界

后台接口统一挂在：

```text
/api/admin/*
```

核心依赖是：

```python
require_admin_user
```

它的作用是：

```text
未登录用户 -> 401
普通用户 -> 403
管理员 -> 放行
```

这点很重要：

```text
前端隐藏后台按钮只是用户体验。
真正安全必须靠后端接口鉴权。
```

面试时不要说“我前端判断 role 是 admin 才显示后台，所以安全”。正确说法是：

```text
前端只做入口可见性控制，后端每个 /api/admin/* 接口都通过 require_admin_user 做权限拦截。
```

## 4. 当前后台接口

当前已经有：

```text
GET /api/admin/summary
GET /api/admin/config
GET /api/admin/users
GET /api/admin/rag/documents
GET /api/admin/rag/logs
GET /api/admin/agent/logs
```

它们分别用于：

```text
summary：平台统计概览
config：当前模型、embedding、rerank、数据库配置摘要
users：用户只读列表
rag/documents：RAG 文档只读列表
rag/logs：RAG 命中日志只读列表
agent/logs：Agent 决策日志只读列表
```

## 5. 前端后台如何接入

前端新增了三个关键 DOM：

```text
adminNavButton
adminDashboardPanel
adminDashboardContent
```

核心函数是：

```javascript
isAdminUser()
renderAdminVisibility()
loadAdminDashboard()
renderAdminDashboard()
```

职责分别是：

```text
isAdminUser：判断当前登录用户 role 是否为 admin。
renderAdminVisibility：管理员显示后台入口，普通用户隐藏后台入口。
loadAdminDashboard：并发请求后台 summary、用户、文档、RAG 日志、Agent 日志。
renderAdminDashboard：把后台数据渲染成统计卡片和只读列表。
```

## 6. 为什么后台也要看 RAG 和 Agent 日志

AI 应用最怕黑箱。

如果用户说：

```text
为什么这道题这么问？
为什么一直追问某个知识点？
为什么 RAG 没查到我的简历内容？
```

后台至少要能看：

```text
RAG 查询语句是什么？
命中了几个 chunk？
使用了哪个 retriever？
Agent 下一步动作是什么？
Agent 的 focus、reason、fallbackUsed 是什么？
```

所以后台不是装饰页面，而是工程化可观测能力的一部分。

## 7. 测试覆盖了什么

后端测试：

```text
tests/test_admin_auth.py
tests/test_admin_routes.py
```

覆盖：

```text
普通用户访问后台接口会 403。
管理员可以访问 summary/config/list 接口。
后台列表返回 users、documents、RAG logs、Agent logs。
```

前端测试：

```text
tests/frontend_admin_permissions.test.mjs
tests/frontend_admin_dashboard.test.mjs
```

覆盖：

```text
普通用户隐藏后台入口。
管理员显示后台入口。
管理员后台会调用正确的 GET 接口。
后台面板能渲染用户、RAG 文档、RAG 日志、Agent 日志。
页面不出现 undefined。
```

## 8. 面试时怎么讲

可以这样表达：

```text
我给系统补了一个管理员后台 MVP。后端把后台能力统一收敛到 /api/admin/*，通过 require_admin_user 做权限控制，普通用户访问会返回 403。第一版后台只做只读列表，包括用户、RAG 文档、RAG 命中日志和 Agent 决策日志，避免一开始引入删除、封禁、复杂 RBAC 等高风险操作。前端根据用户 role 控制后台入口显示，但真正安全边界在后端。后台的价值是提升 AI 应用可观测性，方便排查 RAG 召回和 Agent 决策问题。
```

如果面试官问“为什么不做完整 RBAC”，可以回答：

```text
当前项目处于产品化 MVP 阶段，只需要区分 user/admin 两类角色。复杂 RBAC 会引入菜单权限、资源权限、组织权限等额外复杂度，第一版先保证后台只读和权限隔离，后续再按需求升级。
```
