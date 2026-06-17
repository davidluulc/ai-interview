# 13. Vue3 管理员后台如何承接权限和 AI 可观测性

## 1. 这一轮到底做了什么

这一轮做的是 Vue3 管理员后台 V1。

它不是“随便加一个后台页面”，而是把项目里已经存在的后端管理员能力接到 Vue3 前端里：

- 普通用户登录后看不到“后台”入口。
- 管理员登录后能看到“后台”入口。
- 普通用户手动访问 `/vue/app/admin` 时，会看到无权限提示。
- 管理员访问 `/vue/app/admin` 时，可以看到平台概览、账号管理、RAG 质量诊断、RAG 文档概览、Agent 决策日志和系统配置。

这个阶段只做只读后台，不做删除用户、禁用账号、重置密码、修改角色等高风险写操作。

## 2. 前端权限和后端权限的区别

前端根据 `auth.user.role` 判断当前用户是不是管理员。

这个判断只负责用户体验，比如：

- 是否显示“后台”导航入口。
- 普通用户访问后台页面时是否显示无权限提示。

但真正的安全边界必须在后端。

后端所有 `/api/admin/*` 接口仍然依赖 `require_admin_user`：

```text
未登录用户 -> 401
普通用户 -> 403
管理员 -> 放行
```

所以面试时不能说“前端隐藏按钮就实现了权限控制”。

更专业的表达是：

```text
前端 role 判断只做体验层控制，真正的权限校验在后端 admin 接口里完成。即使普通用户绕过前端直接请求 /api/admin/*，后端仍然会返回 403。
```

## 3. 为什么新增 admin API client 和 admin store

页面组件不应该到处直接写 `fetch`。

这一轮把后台请求拆成两层：

```text
frontend/src/api/admin.ts
```

负责封装只读后台接口，例如：

- `fetchAdminSummary`
- `fetchAdminUsers`
- `fetchAdminRagDocuments`
- `fetchAdminRagQuality`
- `fetchAdminAgentLogs`
- `fetchAdminConfig`

```text
frontend/src/stores/admin.ts
```

负责维护后台页面状态，例如：

- `summary`
- `users`
- `ragDocuments`
- `ragQuality`
- `agentLogs`
- `config`
- `loading`
- `error`
- `userSearch`
- `roleFilter`
- `filteredUsers`

这样做的好处是：

- 请求逻辑集中在 API 层。
- 页面状态集中在 Pinia store。
- 页面组件主要负责渲染和交互。
- 后续如果后台接口字段变化，优先改 API/store，不需要到处改页面。

## 4. 登录态恢复为什么重要

浏览器刷新页面后，Pinia 内存里的 `auth.user` 会丢失，但 localStorage 里的 token 还在。

如果页面一加载就判断：

```text
auth.isAdmin === false
```

就可能误把管理员判断成普通用户。

所以这一轮补了启动恢复逻辑：

```text
App.vue 启动 -> auth.restore() -> /api/auth/me -> 恢复当前用户信息
```

管理员页也做了中间态：

```text
正在恢复登录状态
```

恢复完成后，如果用户是管理员，再加载后台数据。

面试表达可以这样说：

```text
我处理了刷新后台页时的登录态恢复问题。因为 token 在 localStorage，但用户信息在 Pinia 内存里，刷新后 user 会先为空。为了避免管理员刷新后台页时被误判成无权限，我在 App 启动时调用 restore 拉取当前用户，并在 AdminPage 里增加恢复中状态和 isAdmin 监听，等身份恢复后再加载后台数据。
```

## 5. AI 可观测后台展示什么

管理员后台不是只看用户列表，它还承接了 AI 应用工程化里的可观测能力。

RAG 质量诊断展示：

- 低质量召回数量。
- 空召回数量。
- 弱召回数量。
- 未进入 Prompt 的数量。
- 低质量样例和改进建议。

Agent 决策日志展示：

- 下一步动作。
- 当前阶段。
- 难度。
- 关注点。
- 决策原因。
- 是否使用 fallback。

这能说明项目不是只会“调大模型接口”，而是能观察 RAG 和 Agent 的运行过程。

## 6. 为什么 V1 不做后台写操作

删除用户、禁用账号、修改角色、重置密码都属于高风险操作。

如果要做，至少要补：

- 操作审计日志。
- 二次确认。
- 最后一个管理员保护。
- 管理员不能禁用自己。
- 回滚或恢复方案。
- 更完整的 RBAC 权限模型。

所以 V1 先做低风险只读后台，更符合渐进式开发。

面试表达可以这样说：

```text
管理员后台 V1 我只做了只读能力，没有急着做删除、禁用、改角色。因为这些属于高风险写操作，需要配套审计日志、自我保护、最后一个管理员保护和二次确认。当前阶段先把权限边界、数据展示和 AI 可观测能力做扎实。
```

## 7. 这一轮测试覆盖了什么

这一轮遵循 TDD：

- 先写 auth store 测试，再增加 `isAdmin`。
- 先写 layout 测试，再隐藏普通用户的后台入口。
- 先写 admin store 测试，再实现后台数据 store。
- 先写 admin page 测试，再实现管理员后台页面。
- 浏览器验证发现刷新后台页误判权限后，补了登录态恢复测试。
- 浏览器验证发现移动端横向溢出后，修复外层布局溢出。

验证命令包括：

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

以及后端 admin 测试：

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_admin_rag_quality.py -q
```

## 8. 面试时怎么讲这一轮

可以这样讲：

```text
我在 Vue3 前端里补了管理员后台 V1。前端通过 auth.user.role 控制后台入口展示，普通用户看不到后台入口，管理员能看到；但真正的权限校验仍然放在后端 /api/admin/*，由 require_admin_user 保证普通用户即使绕过前端也访问不了后台接口。

后台采用只读设计，包含平台概览、账号列表、RAG 质量诊断、RAG 文档概览、Agent 决策日志和系统配置。这样管理员可以观察系统运行状态，尤其是 RAG 是否空召回、弱召回，以及 Agent 是否频繁 fallback，避免 AI 应用黑箱化。

前端结构上，我把请求封装到 admin API client，把后台状态放进 Pinia admin store，页面组件只负责渲染和交互。同时我处理了刷新页面后的登录态恢复问题，避免管理员刷新后台时因为 user 尚未恢复而被误判成无权限。
```

## 9. 当前边界

当前已经完成：

- Vue3 管理员后台只读 V1。
- 普通用户和管理员的入口差异。
- 管理员后台数据展示。
- 登录态恢复。
- 移动端基本适配。

当前尚未做：

- 后台写操作。
- 复杂 RBAC。
- 审计日志页面。
- 用户禁用、删除、改角色。
- 管理员后台分页、导出和高级筛选。

这些可以作为后续 V2 独立规划。
