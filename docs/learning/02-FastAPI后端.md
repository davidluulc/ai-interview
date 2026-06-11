# FastAPI 后端

## 后端整体结构

当前后端核心是：

```text
FastAPI
-> routes 接收 HTTP 请求
-> schemas 校验请求/响应数据
-> db_models 定义数据库表
-> database 管理数据库连接和会话
-> service / rag / agent 模块处理业务逻辑
```

## routes 是什么

`routes` 目录里的文件负责定义接口。

例如：

- 用户登录注册；
- 简历档案；
- 面试下一题；
- RAG 文档管理；
- 管理员后台。

你可以把路由理解为：

```text
前端请求进来的入口
```

## schemas 是什么

schemas 用 Pydantic 定义接口数据格式。

它负责：

- 字段类型校验；
- 默认值；
- 请求参数是否合法；
- 返回结构是否稳定。

比如用户传错类型时，FastAPI 会返回 422。

## db_models 和 database 的关系

`db_models.py` 定义表结构，例如用户表、面试记录表、RAG 文档表。

`database.py` 负责：

- 创建数据库 engine；
- 创建 SessionLocal；
- 提供 `get_db()`；
- 初始化表；
- 处理 SQLite 兼容迁移。

简单说：

```text
db_models 说明有哪些表
database 负责怎么连接和操作数据库
```

## Depends 是什么

`Depends(get_db)` 表示给接口注入数据库会话。

`Depends(get_current_user)` 表示给接口注入当前登录用户，同时完成鉴权。

面试表达：

```text
FastAPI 的 Depends 是依赖注入机制。
我用它把数据库会话和当前登录用户注入到接口函数里，这样接口不需要手动解析 token 或手动创建数据库连接。
```

## 鉴权

当前项目有用户系统，使用 token 保护需要登录的接口。

常见链路：

```text
注册
-> 登录
-> 获得 access token / refresh token
-> 请求接口时带 Authorization header
-> 后端解析 token
-> 找到当前用户
```

## 测试

后端测试主要用 pytest。

重点覆盖：

- 鉴权；
- 路由接口；
- RAG 检索；
- Agent 决策；
- 管理员后台；
- 数据库模型关系。

