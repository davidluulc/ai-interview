# 公网演示资料

更新时间：2026-06-18

本文件用于公网演示和完整链路 smoke test。所有内容都是虚构资料，不包含真实个人隐私。

## 1. 演示目标

用下面这份虚构档案走完整链路：

```text
注册或登录
-> 创建投递档案
-> 开始面试
-> 回答 3-5 轮
-> 结束面试
-> 查看复盘报告
-> 查看训练任务
-> 管理员后台查看 RAG / Agent / LangGraph 观测信息
```

## 2. 档案信息

档案标题：

```text
后端开发实习 - 智能招聘平台
```

目标岗位：

```text
Python 后端开发实习生
```

投递类型：

```text
实习
```

职位标签：

```text
python_backend_intern
```

## 3. 虚构简历

```text
姓名：林一舟
身份：计算机科学与技术专业大三学生
目标岗位：Python 后端开发实习生

教育经历：
- 华东某高校，计算机科学与技术，本科，2023.09 - 2027.06
- 主修课程：数据结构、操作系统、计算机网络、数据库系统、软件工程、Python 程序设计

技术栈：
- 编程语言：Python、JavaScript、TypeScript
- 后端框架：FastAPI、Flask
- 数据库：SQLite、MySQL、PostgreSQL 基础
- ORM / 迁移：SQLAlchemy、Alembic
- 中间件：Redis 基础、Celery 基础
- AI 应用：RAG、Embedding、Prompt Engineering、LangGraph 基础
- 前端：HTML、CSS、Vue3 基础
- 工程工具：Git、Docker、Docker Compose、Linux 基础命令

项目经历：
1. AI 模拟面试系统
- 面向大学生和求职者，支持用户创建投递档案，输入简历和岗位 JD 后进行模拟面试。
- 后端使用 FastAPI，数据库使用 SQLAlchemy，生产部署支持 PostgreSQL。
- 设计岗位知识库 RAG、题库 RAG、候选人画像 RAG 三类检索来源，为面试题生成提供上下文。
- 引入 Agent State、Agent Decision、fallback 和日志记录，提升面试过程可观测性。
- 使用 Vue3 搭建用户工作台和管理员后台，管理员可查看 RAG 命中、Agent 决策和异步任务状态。
- 使用 Docker Compose 部署 FastAPI、PostgreSQL、Redis、Celery worker 和 Nginx。

2. 校园二手交易小程序后端
- 负责商品发布、搜索、收藏和订单状态接口。
- 使用 Flask + MySQL 实现 RESTful API。
- 通过 Redis 缓存热门商品列表，降低数据库查询压力。

实习和实践：
- 参与学校软件工程课程项目，担任后端开发角色。
- 有基础 Linux 部署经验，能独立阅读日志定位接口错误。

优势：
- 熟悉 Python Web 后端基础开发流程。
- 对 AI 应用工程化、RAG 和 Agent 可观测性有实践兴趣。
- 能结合业务场景解释技术选型，不只停留在调用模型 API。
```

## 4. 虚构岗位 JD

```text
岗位名称：Python 后端开发实习生

岗位职责：
1. 参与智能招聘和人才评估平台的后端接口开发。
2. 负责用户、简历、岗位、面试记录等业务模块的 API 设计与实现。
3. 参与 RAG、LLM 应用和数据处理链路的工程化开发。
4. 配合前端完成接口联调，保证接口稳定性和错误提示清晰。
5. 参与数据库表设计、SQL 查询优化和基础部署排错。

任职要求：
1. 熟悉 Python 语言，了解 FastAPI、Flask 或 Django 任一 Web 框架。
2. 熟悉 HTTP、RESTful API、鉴权、异常处理和接口文档。
3. 熟悉 SQL 基础，了解 MySQL 或 PostgreSQL，了解 ORM 使用方式。
4. 了解 Redis、消息队列或异步任务者优先。
5. 对大模型应用、RAG、Agent、LangGraph 有了解或实践者优先。
6. 具备 Git、Linux、Docker 基础使用经验。
7. 有较强学习能力，能够把业务问题拆解成后端模块和数据流。

加分项：
- 有 AI 应用项目经验。
- 有部署上线、日志排查、数据库迁移经验。
- 能解释 RAG 和普通 LLM 调用的区别。
- 能说明 Agent 状态、工具调用、决策日志和 fallback 的价值。
```

## 5. 虚构公司信息

```text
公司名称：星桥智能科技

业务方向：
星桥智能科技是一家面向高校就业中心和企业招聘团队的 AI 人才评估平台，主要提供简历解析、岗位匹配、AI 模拟面试和面试复盘服务。

当前团队关注：
- 如何让 AI 面试问题更贴近候选人经历和岗位要求。
- 如何通过 RAG 降低大模型泛泛而谈的问题。
- 如何通过日志和后台观测减少 AI 黑箱问题。
- 如何把 AI 应用从 Demo 推进到可部署、可维护的工程系统。
```

## 6. 建议回答样例

第一轮可以简单回答：

```text
我做过一个 AI 模拟面试系统，主要负责后端接口、RAG 文档管理、Agent 决策链路和部署上线。项目里用户会先创建投递档案，输入简历和岗位 JD，系统再结合岗位知识库、题库和候选人画像生成面试题。
```

如果系统追问 RAG，可以回答：

```text
我把 RAG 拆成三类：岗位知识库、题库和候选人画像。岗位知识库保证问题贴近 JD 和技术栈，题库保证问题有真实面试语境，候选人画像保证问题能结合用户自己的简历经历。这样比单纯把所有内容混在一起更容易维护，也更方便记录命中质量。
```

如果系统追问部署，可以回答：

```text
我用 Docker Compose 编排 FastAPI、PostgreSQL、Redis、Celery worker 和 Nginx。上线时遇到过本地 SQLite 和生产 PostgreSQL schema 不一致的问题，后来通过查看后端日志定位到缺少 Alembic 迁移字段，并补充了幂等迁移和测试。
```

## 7. 管理员后台验收点

完成一场面试后，用管理员账号查看：

- 用户数量是否增加。
- Agent 决策日志是否出现新记录。
- AI Debug 或 Agent 工作流观测里是否能看到 runtime、fallback、quality gate、nodeTrace。
- RAG 质量诊断是否能看到命中摘要。
- RAG 文档上传后，RAG 摄取任务是否能显示 queued/running/succeeded/failed 状态。

如果页面出现 `Internal server error`，优先查看：

```text
sudo docker compose --env-file .env.production logs app --tail=200
```

这通常不是 Vue 页面坏了，而是后端接口、数据库迁移、环境变量或中间件状态出了问题。
