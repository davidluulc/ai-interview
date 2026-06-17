# Project Closure Audit V1：项目阶段性收口审计与开发基线整理

更新时间：2026-06-17

## 1. 背景

AI 模拟面试系统已经经历多轮功能开发，当前已经具备：

- FastAPI 后端、SQLAlchemy ORM、SQLite 本地开发数据库、Alembic 迁移脚本。
- 用户注册、登录、refresh token、管理员权限。
- Vue3 主前端、投递档案、面试工作台、知识库页面、复盘页、训练中心、管理员后台。
- 三类 RAG、文档管理、摄取任务、检索日志、质量评估、hybrid / rerank 等工程化能力。
- Agent Orchestrator、LangGraph runtime、checkpoint、quality gate、fallback、runtime audit 和后台工作流观测。
- 后端 pytest、前端 Vitest、Vue 类型检查和 Vite build。

项目已经从“功能验证”进入“继续生产化增强前的基线整理”阶段。下一步计划可能会继续开发 RAG 生产化、Redis、Celery、PostgreSQL 等后端基础设施。如果不先做阶段性收口，后续容易出现以下问题：

- active / completed / archive 文档边界不清，旧 spec 影响新路线判断。
- README、启动脚本、Vue3 主入口、旧原生前端入口表达不一致。
- 新开发者或未来的自己无法快速判断当前主链路是什么。
- 后续引入中间件时，容易把历史兼容入口、旧脚本、旧文档当成当前主线。

本阶段目标不是停止开发，而是建立一个清晰、可维护、可继续扩展的开发基线。

## 2. 本阶段目标

完成后，项目应具备：

1. 清晰的当前项目状态说明：当前主前端、主后端、主 Agent 链路、RAG 状态、数据库状态。
2. 清晰的启动入口：本地开发时如何启动后端、Vue3 前端、如何访问主页面。
3. 清晰的测试入口：后端测试、前端测试、前端构建命令明确。
4. 清晰的文档入口：`docs/roadmap/current-state.md`、`docs/specs/README.md`、`docs/plans/README.md` 不互相打架。
5. 清晰的历史文档状态：active 只放当前阶段，completed 只放已完成阶段，archive 只放背景资料。
6. 清晰的兼容入口说明：旧原生前端、旧脚本、旧文档如果仍保留，需要标注为什么保留。
7. 清晰的后续开发前置条件：为 Backend Production Infrastructure V1、RAG 生产化增强、Redis/Celery/PostgreSQL 留出干净基线。
8. 一份面向开发维护的基线文档，而不是完整项目讲解稿。

## 3. 非目标

本阶段明确不做：

- 不新增业务功能。
- 不做完整项目讲解稿。
- 不写简历项目描述。
- 不做八股文学习文档。
- 不引入 Redis。
- 不引入 Celery。
- 不切换 PostgreSQL。
- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不重构 RAG 检索、摄取、rerank、evaluation 主链路。
- 不重构 Agent / LangGraph 主链路。
- 不重构 Vue3 整站 UI。
- 不删除无法确认是否仍被引用的代码、脚本或文档。
- 不清空本地数据库。

如果审计中发现明显风险，只记录为后续任务；除非非常确定且有测试覆盖，否则不在本阶段做破坏性清理。

## 4. 审计范围

### 4.1 文档结构

需要检查：

- `README.md`
- `docs/roadmap/current-state.md`
- `docs/specs/README.md`
- `docs/plans/README.md`
- `docs/specs/active/`
- `docs/plans/active/`
- `docs/specs/completed/`
- `docs/plans/completed/`
- `docs/specs/archive/`
- `docs/plans/archive/`

关注点：

- 是否有 active 文档残留。
- completed 文档是否仍被误认为待执行。
- roadmap 是否准确描述当前状态。
- README 是否能作为项目入口。
- 是否存在互相矛盾的“下一步开发建议”。

### 4.2 启动入口

需要检查：

- 后端启动脚本。
- Vue3 前端启动脚本。
- 旧启动脚本是否仍作为兼容入口保留。
- `localhost:8000` 和 `localhost:5173` 的职责说明。
- 是否存在会把用户带到旧页面的入口。

期望表达：

```text
8000：FastAPI 后端 API / 旧兼容入口。
5173：Vue3 当前主前端开发入口。
```

### 4.3 前端入口

需要检查：

- 当前主前端是否明确为 Vue3。
- `/vue/app/interview`、`/vue/app/admin`、`/vue/app/knowledge`、`/vue/app/training` 等主页面是否仍然可访问。
- 旧原生页面是否保留为兼容入口。
- README 是否明确建议优先访问 Vue3。

### 4.4 后端主链路

需要检查：

- `/api/interview/next-question` 当前默认内部 runtime 是否为 `langgraph_mainline`。
- `classic` 是否仅作为 fallback/helper 保留。
- RAG 是否仍作为 retrieve_context 节点复用现有能力。
- 后台观测入口是否能说明 Agent workflow、RAG、checkpoint、fallback、quality gate。

本阶段只做文档和基线确认，不改 Agent/RAG 业务逻辑。

### 4.5 测试和构建

需要确认并写入基线文档：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

必要时可以补充更短的 focused test 建议，但不能让 README 变成测试大全。

### 4.6 本地开发账号

需要检查是否有清晰的本地开发账号说明。

建议只记录开发环境账号用途，不在 README 中强调真实用户隐私信息。可以使用：

```text
普通演示账号：d77013643@gmail.com / 123456
管理员演示账号：1011569954@qq.com / 123456
```

如果账号不存在，后续 implementation plan 可选择提供本地 seed 脚本或说明如何注册/提升管理员权限。

### 4.7 临时文件和生成物

需要检查：

- 是否有明显临时文件。
- 是否有不应提交的构建产物。
- 是否有重复启动脚本。
- 是否有历史截图、缓存、日志文件误入项目。

处理原则：

```text
能确定无用的，删除。
不能确定的，先记录，不删除。
需要保留兼容的，标注用途。
```

## 5. 产出物

本阶段建议产出：

1. 更新 `README.md`
   - 明确项目定位。
   - 明确启动方式。
   - 明确主前端入口。
   - 明确测试命令。
   - 明确当前技术栈和主链路。

2. 更新 `docs/roadmap/current-state.md`
   - 标注当前 active 阶段为 Project Closure Audit V1。
   - 记录 LangGraph Mainline Consolidation V7 已完成。
   - 记录下一阶段建议仍需重新讨论，不直接执行旧文档。

3. 新增或更新 `docs/project-baseline.md`
   - 作为项目当前开发基线入口。
   - 说明目录结构、主入口、启动方式、测试方式、兼容入口、后续开发边界。

4. 可选新增 `docs/development-guide.md`
   - 如果 README 不适合写太长，可以把详细开发说明放这里。
   - README 只保留快速启动和文档索引。

5. 更新 `docs/specs/README.md` 和 `docs/plans/README.md`
   - 明确当前 active spec / plan。
   - 避免 completed 文档被误执行。

6. 形成一份审计清单
   - 记录已检查项。
   - 记录不处理的遗留项。
   - 记录下一阶段进入 Redis/Celery/PostgreSQL 前的注意事项。

## 6. 建议实施顺序

本阶段 implementation plan 应按低风险顺序执行：

1. 只读审计：扫描 README、docs、启动脚本、前后端入口、测试命令、Git 状态。
2. 建立基线文档：新增 `docs/project-baseline.md`。
3. 更新 README：只写当前可靠入口，不写过度承诺。
4. 更新 docs README 和 roadmap：让 active/completed 状态统一。
5. 检查明显临时文件：只删除能确认无用的文件。
6. 运行后端测试、前端测试、前端构建。
7. 使用浏览器打开 Vue3 主页面和后台页面做最小验证。
8. 归档本 spec 和对应 plan。

## 7. 验收标准

完成后必须满足：

- `README.md` 能指导用户启动项目。
- `docs/project-baseline.md` 能说明当前项目开发基线。
- `docs/roadmap/current-state.md` 当前状态与代码事实一致。
- `docs/specs/README.md` 和 `docs/plans/README.md` 不再误导执行旧阶段。
- `docs/specs/active/` 和 `docs/plans/active/` 状态清晰。
- Vue3 是明确的当前主前端。
- 旧原生前端如保留，必须说明是兼容入口。
- 后端主链路明确为 LangGraph mainline + classic fallback。
- RAG/Agent/训练闭环/管理员后台当前能力有简要索引。
- 后续 Redis/Celery/PostgreSQL 仍是下一阶段候选，不在本阶段实现。
- `python -m pytest -q` 通过。
- `frontend` 下 `npm.cmd run test` 通过。
- `frontend` 下 `npm.cmd run build` 通过。
- 浏览器验证 Vue3 主入口和管理员后台可以打开。

## 8. 风险和约束

### 8.1 最大风险：误删历史兼容文件

项目历史较长，旧文件可能仍被测试、脚本或兼容入口引用。本阶段不能为了“看起来干净”盲目删除文件。

处理方式：

- 删除前必须确认没有引用。
- 删除前必须确认测试覆盖。
- 不确定就记录，不删除。

### 8.2 第二风险：把收口审计做成大重构

本阶段只做基线整理，不改业务主链路。发现 RAG、Agent、Vue3、数据库设计问题时，记录为后续 spec，不在本阶段扩散。

### 8.3 第三风险：文档过度膨胀

README 应该短而准；详细说明放 `docs/project-baseline.md` 或 `docs/development-guide.md`。不要把 README 写成完整学习手册。

## 9. 面试表达种子

本阶段完成后，可以这样解释它的工程价值：

```text
在继续做 Redis、Celery、PostgreSQL 和 RAG 生产化之前，我先做了一轮项目收口审计。
这不是新增业务功能，而是建立开发基线：统一 README、启动入口、测试命令、文档状态和主链路说明。
这样后续引入中间件时，不会被旧页面、旧脚本、旧 spec 干扰，也能让项目更容易被维护和交接。
```

这段只是种子，不是完整项目讲解稿。

## 10. 下一阶段衔接

本阶段完成后，再讨论是否进入：

```text
Backend Production Infrastructure V1：PostgreSQL + Redis + Celery 后端生产化底座
```

建议下一阶段优先级：

1. 保留 SQLite 本地默认开发，同时增强 PostgreSQL 配置兼容。
2. 引入 Redis 健康检查和缓存/限流/token blacklist 预留。
3. 引入 Celery + Redis broker，把 RAG 摄取任务改造成异步任务。
4. 管理员后台展示异步任务状态、失败原因、重试次数和耗时。

这些不属于 Project Closure Audit V1 的实现范围。
