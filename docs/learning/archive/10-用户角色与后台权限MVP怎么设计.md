# 10 用户角色与后台权限 MVP 怎么设计

## 1. 本阶段解决什么问题

本阶段给系统补上最小管理员权限基础。

以前系统只有“是否登录”的概念：

```text
未登录 -> 不能访问受保护接口
已登录 -> 可以访问自己的历史记录、RAG 文档、面试功能
```

但产品化后会出现后台管理端，例如：

- 用户列表。
- 知识库管理。
- 题库管理。
- RAG 日志。
- Agent 决策日志。

这些内容不能让普通用户访问，所以系统需要区分：

```text
普通用户 user
管理员 admin
```

## 2. 为什么只做 user/admin 两种角色

第一版后台不做复杂 RBAC。

RBAC 是 Role-Based Access Control，意思是基于角色的权限控制。完整 RBAC 可能包含：

- 角色。
- 权限点。
- 菜单权限。
- 数据权限。
- 角色和权限的绑定关系。

这些对当前项目来说太重了。

当前只需要：

```text
user：使用面试、训练、历史、档案等用户端功能。
admin：在 user 能力基础上，额外访问后台管理接口。
```

这样能先把后台 MVP 跑通，又不会一开始把权限系统做复杂。

## 3. get_current_user 和 require_admin_user 的区别

`get_current_user` 解决的是：

```text
当前请求是谁发来的？
```

它会读取请求里的 `Authorization: Bearer <token>`，解析 JWT，找到当前用户。

`require_admin_user` 解决的是：

```text
当前用户是不是管理员？
```

它复用 `get_current_user`，然后检查：

```python
current_user.role == "admin"
```

如果不是管理员，就返回 403。

区别可以这样记：

```text
get_current_user：证明你是谁。
require_admin_user：证明你有没有后台权限。
```

## 4. 为什么前端隐藏入口不等于权限控制

前端可以根据：

```text
authState.user.role
```

决定是否显示“后台管理”入口。

但这只是用户体验。

真正的权限必须放在后端，因为用户可以绕过前端，直接请求：

```text
GET /api/admin/summary
```

所以后台接口必须使用：

```python
Depends(require_admin_user)
```

这样普通用户即使手动请求后台接口，也会得到 403。

## 5. 关键代码位置

用户角色字段：

```text
backend_python/db_models.py
```

SQLite 旧库兼容补列：

```text
backend_python/database.py
```

当前用户和管理员依赖：

```text
backend_python/auth.py
```

认证响应返回 `role`：

```text
backend_python/routes/auth.py
```

管理员 summary 接口：

```text
backend_python/routes/admin.py
```

路由注册：

```text
backend_python/main.py
```

测试：

```text
tests/test_admin_auth.py
tests/test_admin_routes.py
```

## 6. 面试时怎么讲

可以这样说：

```text
我在项目里给用户系统补了最小后台权限模型。第一版没有做复杂 RBAC，只区分 user 和 admin 两种角色。普通用户只能访问自己的面试、训练和历史数据；管理员可以访问 /api/admin 下的后台接口。

实现上我在 users 表增加 role 字段，默认是 user。后端保留 get_current_user 负责解析 token 和获取当前用户，又新增 require_admin_user 依赖，用来检查 current_user.role 是否为 admin。所有后台接口都挂这个依赖，所以即使普通用户绕过前端直接请求后台接口，也会返回 403。
```

## 7. 当前边界

当前阶段已经完成：

- `User.role`。
- 登录、刷新、`/me` 返回 role。
- `require_admin_user`。
- `/api/admin/summary`。
- `/api/admin/config`。
- 普通用户访问后台返回 403。
- 未登录访问后台返回 401。

当前还没有完成：

- 后台用户列表。
- 后台 RAG 文档列表。
- 后台 RAG 日志列表。
- 后台 Agent 日志列表。
- 前端后台入口。
- 复杂 RBAC。
- 强制下线或封禁用户。

这些会在后续阶段继续做。

