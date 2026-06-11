# 数据库迁移工程化设计

## 背景

当前项目已经使用 FastAPI + SQLAlchemy + SQLite 保存面试历史记录。这个方案适合本地开发，但如果后续项目要上线到云服务器，数据库表结构不能只靠 `Base.metadata.create_all()` 自动创建。

原因是：上线后的数据库会长期保存真实用户数据，表结构每次变化都需要可追踪、可重复执行、可回滚。Alembic 的作用就是管理这些数据库表结构变化。

## Alembic 是什么

可以把 Alembic 理解成“数据库表结构的 Git”。

Git 负责记录代码版本：

```text
第一次提交：新增后端
第二次提交：新增 RAG
第三次提交：新增历史记录
```

Alembic 负责记录数据库表结构版本：

```text
第一版迁移：创建 interview_records 表
第二版迁移：给 interview_records 增加 user_id 字段
第三版迁移：新增 users 表
```

开发者不应该在生产数据库里手动点按钮建表，而应该用迁移脚本让数据库结构跟着代码版本升级。

## 本轮目标

本轮采用“保守升级”的方案：

- 本地开发默认继续使用 SQLite，降低启动成本。
- 数据库连接继续通过 `DATABASE_URL` 配置。
- 引入 Alembic 管理数据库表结构。
- 创建第一版迁移脚本，用来创建 `interview_records` 表。
- README 增加中文说明，解释 SQLite 开发模式、PostgreSQL 上线模式和 Alembic 常用命令。
- 增加测试，保证数据库模型和配置不会被后续改坏。

## 本轮不做什么

为了控制学习成本，本轮暂时不做这些内容：

- 不强制把本地数据库切换成 PostgreSQL。
- 不引入 Docker Compose。
- 不引入 Redis。
- 不引入用户登录和多用户隔离。
- 不把所有数据库访问改成 async SQLAlchemy。

这些内容适合放到后续阶段逐步做。

## 目标架构

```text
FastAPI 路由
  ↓
SQLAlchemy Session
  ↓
SQLAlchemy Model: InterviewRecord
  ↓
DATABASE_URL
  ├─ 本地开发：SQLite
  └─ 上线环境：PostgreSQL

Alembic
  ↓
读取 SQLAlchemy Model
  ↓
生成和执行数据库迁移脚本
```

## 数据流

用户完成一次模拟面试后：

1. 前端点击保存报告。
2. FastAPI 接收报告数据。
3. 路由层创建 `InterviewRecord`。
4. SQLAlchemy Session 把记录写入数据库。
5. Alembic 不参与每次写入，它只负责“数据库表结构怎么创建和升级”。

这点很重要：Alembic 不是 ORM，也不是数据库，它是迁移工具。

## 错误处理

本轮会保持现有错误处理方式：

- 接口运行时数据库异常继续由 FastAPI 错误处理中间件记录日志。
- Alembic 迁移失败时，由命令行输出错误，开发者根据报错修复迁移脚本或数据库连接配置。

后续上线阶段可以进一步增加启动前迁移检查。

## 测试策略

本轮测试重点不是连接真实 PostgreSQL，而是验证工程结构正确：

- `DATABASE_URL` 仍然可以从环境变量配置。
- `InterviewRecord` 表名和核心字段存在。
- 现有历史记录、候选人画像、RAG 相关测试继续通过。

这样可以保证升级迁移体系时不破坏现有功能。

## 学习收益

做完本轮后，可以把项目讲成：

> 开发环境默认使用 SQLite 降低启动成本，数据库访问层通过 SQLAlchemy 抽象；为了支持未来上线，我引入 Alembic 管理表结构迁移。生产环境可以通过 `DATABASE_URL` 切换 PostgreSQL，并通过迁移脚本创建和升级表结构，避免手动建表带来的不可追踪风险。

这是一段很适合写进项目复盘和面试表达里的内容。
