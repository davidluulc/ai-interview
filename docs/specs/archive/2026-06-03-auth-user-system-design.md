# 用户认证系统设计

## 背景

当前 AI 模拟面试系统已经可以保存历史面试记录，但所有记录都在同一张 `interview_records` 表里，没有真正的用户归属。

如果项目未来上线，必须解决两个问题：

1. 谁可以登录系统。
2. 每条面试记录属于哪个用户。

因此本轮要加入正式认证版 MVP：用户表、双 token 认证、refresh token 持久化、历史记录按用户隔离。

## 本轮目标

- 新增 `users` 表，存储邮箱、用户名、密码哈希和创建时间。
- 新增 `refresh_tokens` 表，存储 refresh token 哈希、所属用户、过期时间和撤销状态。
- 给 `interview_records` 增加 `user_id` 字段。
- 新增认证接口：
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/refresh`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
- 使用 JWT access token 访问受保护接口。
- 使用 refresh token 换取新的 access token。
- logout 时撤销 refresh token。
- 历史记录保存、查询、统计和候选人画像召回按当前用户隔离。
- 前端增加最小登录/注册入口，避免认证上线后页面不可用。

## 本轮不做什么

- 不接入 Redis 黑名单。
- 不实现强制踢掉未过期 access token。
- 不做邮箱验证码。
- 不做找回密码。
- 不做多设备会话管理。
- 不做 Vue3 前端重构。

这些内容后续可以单独迭代。

## Token 策略

本轮使用双 token：

```text
access_token：短期 JWT，用来访问接口
refresh_token：长期随机 token，用来换新的 access_token
```

`access_token` 中包含：

```text
sub: 用户 id
type: access
exp: 过期时间
```

`refresh_token` 不直接明文存数据库，而是存哈希：

```text
refresh_tokens.token_hash
```

这样即使数据库泄露，也不会直接暴露可用 refresh token。

## Logout 策略

本轮 logout 的行为是：

1. 前端提交 refresh token。
2. 后端找到对应 token 哈希。
3. 将其标记为 revoked。
4. 后续该 refresh token 不能再换新的 access token。

注意：本轮不做 Redis access token 黑名单，所以 logout 后，已经签发且尚未过期的 access token 理论上仍可使用一小段时间。

后续如果要支持“立即踢人下线”，可以接入 Redis 黑名单，记录 access token 的 `jti`。

## 数据模型

```text
users
  id
  email
  username
  password_hash
  created_at

refresh_tokens
  id
  user_id
  token_hash
  expires_at
  revoked_at
  created_at

interview_records
  user_id
```

`interview_records.user_id` 允许为空，是为了兼容本地已有的旧历史记录。新登录用户保存的记录必须写入当前用户 id。

## 接口设计

### 注册

```text
POST /api/auth/register
```

请求：

```json
{
  "email": "student@example.com",
  "username": "student",
  "password": "password123"
}
```

响应：

```json
{
  "id": 1,
  "email": "student@example.com",
  "username": "student"
}
```

### 登录

```text
POST /api/auth/login
```

响应：

```json
{
  "accessToken": "...",
  "refreshToken": "...",
  "tokenType": "bearer",
  "user": {
    "id": 1,
    "email": "student@example.com",
    "username": "student"
  }
}
```

### 刷新

```text
POST /api/auth/refresh
```

用 refresh token 换新的 access token。

### 退出登录

```text
POST /api/auth/logout
```

撤销 refresh token。

### 当前用户

```text
GET /api/auth/me
```

需要 `Authorization: Bearer <access_token>`。

## 历史记录隔离

认证后：

- 保存历史记录时写入 `user_id=current_user.id`。
- 查询历史记录时只返回 `current_user.id` 的记录。
- 统计历史记录时只统计当前用户记录。
- 候选人画像 RAG 只召回当前用户历史记录。

这一步是未来“不同用户只能查自己的知识库”的前置基础。

## 前端最小接入

本轮只在当前静态前端中增加最小认证能力：

- 登录/注册表单。
- 登录状态展示。
- 退出登录按钮。
- 请求历史记录接口时附带 `Authorization`。
- 未登录时提示先登录再保存或查看历史。

高级感前端框架重构放到后续阶段，建议使用 Vue3 + Vite + TypeScript + Element Plus。

## 测试策略

- 测试密码哈希不能等于明文。
- 测试 access token 可以解析出用户 id。
- 测试注册、登录、获取当前用户流程。
- 测试错误密码不能登录。
- 测试 refresh token 被撤销后不能继续刷新。
- 测试用户 A 看不到用户 B 的历史记录。
- 测试 Alembic 第二版迁移脚本存在。
