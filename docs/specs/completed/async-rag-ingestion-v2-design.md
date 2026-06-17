# Async RAG Ingestion V2：RAG 文档入库 Celery 化

更新时间：2026-06-17

## 1. 背景

当前项目已经完成 Backend Production Infrastructure V1，具备以下基础：

- SQLite 仍作为本地默认开发数据库。
- PostgreSQL 具备配置兼容、数据库类型摘要、URL 脱敏和 Alembic 路径说明。
- Redis 具备 `disabled` / `ok` / `error` 健康检查入口。
- Celery 具备 app 配置、health task、eager mode 测试和基础状态观测。
- 管理员后台可以展示 database、Redis、Celery 基础设施状态。

RAG 侧也已经完成较多工程化能力：

- RAG 文档管理、生命周期、可见性、metadata、chunk 去重。
- 文档上传、文本解析、清洗、chunk 预览和入库。
- `RagIngestionTask` 数据库持久化。
- 用户侧摄取任务历史、失败原因和 retry 入口。
- 管理员后台 RAG 摄取任务监控。

但当前 RAG 文档上传链路仍然偏同步：

```text
HTTP 请求进入后端
-> 后端在请求链路内解析文件、清洗文本、切 chunk、创建 RagDocument / RagChunk
-> 返回任务结果
```

这在小文件和本地开发阶段可以工作，但不适合继续承载更生产化的 RAG 文档入库。文件解析、chunk 切分、后续 embedding 生成、索引构建都属于耗时任务，不应该长期阻塞 HTTP 请求。

本阶段目标是：在不重写 RAG 检索算法、不引入新向量数据库、不做部署上线的前提下，把 RAG 文档入库执行过程迁移到 Celery 任务模型，让 HTTP 接口只负责鉴权、校验、创建任务和返回 `taskId`，由 Celery task 执行后台入库并回写任务状态。

## 2. 本阶段定位

本阶段不是重新做 RAG V3，也不是重写知识库页面。

本阶段是对已有 RAG ingestion 的执行模型升级：

```text
同步入库
-> 任务化入库
-> Celery eager mode 本地可测
-> worker mode 生产可迁移
```

本阶段完成后，项目在面试中的表达会从：

```text
我支持 RAG 文件上传。
```

升级为：

```text
我把 RAG 文档摄取设计成异步任务链路，HTTP 接口只创建任务，Celery worker 负责解析、清洗、chunk 入库，任务状态和失败原因写回数据库，用户端和管理员后台都能观测。
```

## 3. 已有能力与不重复内容

本阶段不重复开发以下已经完成的能力：

- `RagIngestionTask` ORM 模型。
- RAG 摄取任务持久化表。
- 用户侧摄取任务列表和详情。
- 用户侧 retry 接口。
- 管理员侧 RAG 摄取任务监控。
- Vue3 知识库页最近导入任务区域。
- Vue3 管理员后台 RAG 摄取任务监控区域。
- 文档解析、文本清洗、chunk preview、RagDocument / RagChunk 创建逻辑。

本阶段重点是把这些能力接入 Celery task 执行模型，而不是重新做一遍。

## 4. 阶段目标

完成后系统应具备：

1. `POST /api/rag/documents/upload` 创建 `RagIngestionTask` 后，优先投递 Celery ingestion task。
2. Celery eager mode 下，本地测试不需要真实 Redis 或 worker，任务仍能同步执行并通过测试。
3. worker mode 下，接口可以返回 `taskId`，由 worker 后台处理任务。
4. 任务状态流转清晰：

```text
pending -> queued -> running -> succeeded
pending -> queued -> running -> failed
```

如果为了兼容现有代码暂时不新增 `queued` 状态，也必须在 spec/plan 中明确实际状态流转，并保证前端展示不混乱。

5. Celery task 只接收 `taskId`，不直接传大文件内容或复杂对象。
6. task 执行时从数据库读取 `RagIngestionTask.input_json` 或相关快照，再执行解析后续链路。
7. 任务成功后写回 `document_id`、`result_json`、`progress=100`、`status=succeeded`。
8. 任务失败后写回 `status=failed`、`error_message`、`can_retry` 和必要的 `input_json` 快照。
9. retry 不再在 HTTP 请求里同步完整入库，而是重新投递 Celery task 或复用同一任务执行逻辑。
10. 管理员后台能区分“任务已创建但未执行、执行中、成功、失败、可重试”。
11. `/api/admin/config` 或健康检查中已有 Celery 状态继续可用，便于排查 worker/eager 配置。

## 5. 推荐数据流

### 5.1 上传入口

```text
用户上传文件
-> FastAPI 校验鉴权、文件类型、文件大小、metadata
-> 创建 RagIngestionTask(status=pending/progress=0)
-> 保存最小 input snapshot
-> 投递 Celery task: run_rag_ingestion_task.delay(task_id)
-> eager mode 下任务立即执行
-> worker mode 下接口立即返回 taskId
```

接口响应兼容现有前端：

```json
{
  "taskId": "rag_ingestion-xxx",
  "status": "queued",
  "message": "RAG ingestion task queued.",
  "progress": 0,
  "document": null
}
```

如果 eager mode 下已经执行完成，可以返回 `succeeded` 和 `document`，但前端不能依赖任务一定同步完成。

### 5.2 Celery task 执行

```text
run_rag_ingestion_task(task_id)
-> 根据 task_id 查询 RagIngestionTask
-> status=running, progress=10
-> 读取 input_json / textSnapshot / upload snapshot
-> 解析或复用文本快照
-> 文本清洗
-> chunk preview
-> 创建 RagDocument / RagChunk
-> 写 result_json、document_id、status=succeeded、progress=100
```

### 5.3 失败处理

失败应尽量保留可排查信息：

```text
status=failed
progress=100
error_message=可读错误
can_retry=0/1
input_json=可重试所需快照
```

失败分类建议：

- `file_validation_failed`
- `parse_failed`
- `empty_text`
- `invalid_metadata`
- `document_create_failed`
- `celery_dispatch_failed`
- `unexpected_error`

本阶段不要求做复杂错误码系统，但日志和任务表里要能看出失败发生在哪个阶段。

### 5.4 Retry 链路

retry 的核心原则：

```text
复用同一套 Celery task 执行逻辑，不在 retry 接口里重新写一套同步入库逻辑。
```

推荐流程：

```text
POST /api/rag/documents/ingestion-tasks/{task_id}/retry
-> 鉴权：owner 或 admin
-> 校验 status=failed、can_retry=1、retry_count < max_retries
-> retry_count + 1
-> status=pending 或 queued
-> 投递 run_rag_ingestion_task.delay(task_id)
-> 返回 taskId 和当前状态
```

如果 eager mode 下执行完成，可以返回最终结果；worker mode 下返回 queued/running。

## 6. 后端设计边界

### 6.1 建议新增或调整模块

建议新增：

```text
backend_python/tasks/rag_ingestion.py
```

职责：

- 定义 Celery task：`run_rag_ingestion_task`
- task 入参只接受 `task_id`
- task 内部打开数据库 session
- 调用 service 层执行实际摄取
- 捕获异常并回写任务状态

建议调整：

```text
backend_python/rag_ingestion_tasks.py
```

职责从“持久化任务状态工具”扩展为：

- 创建任务。
- 标记 queued / running / succeeded / failed。
- 保存 input snapshot。
- 序列化任务响应。
- 提供 dispatch helper，封装 Celery `.delay()` 和 eager mode 行为。

建议保留：

```text
backend_python/rag_ingestion.py
backend_python/rag_store.py
backend_python/routes/rag_documents.py
```

它们可以被重组调用，但不做大规模重写。

### 6.2 数据库状态

已有 `RagIngestionTask.status` 字段可以继续使用字符串，不急着新增 enum。

状态建议：

```text
pending
queued
running
succeeded
failed
```

如果现有前端或测试已经使用 `success`，本阶段需要做兼容映射，但后端事实状态建议统一为 `succeeded`。

### 6.3 Celery 失败兜底

如果 Celery 投递失败，本阶段不应该让任务消失。

推荐处理：

```text
创建 RagIngestionTask
-> 投递 Celery 失败
-> status=failed
-> error_message="Celery dispatch failed: ..."
-> can_retry=1
-> 返回 503 或返回 failed task，具体由 plan 根据现有接口兼容性决定
```

本地 eager mode 下，大多数测试不需要真实 Redis。

## 7. 前端设计边界

本阶段只允许最小化前端更新。

已有 Vue3 知识库页和管理员后台已经能展示 ingestion task，本阶段只需要补足异步语义：

- 上传后提示“任务已创建/排队中”，不能假设文档立刻出现在列表中。
- 任务状态展示兼容 `queued` / `running`。
- retry 按钮触发后展示“已重新投递/处理中”。
- 管理员后台保留任务监控区，补充 queued/running 的显示文案。

不做：

- 不重构知识库页面整体布局。
- 不新增复杂实时进度条。
- 不引入 WebSocket。
- 不做 SSE。
- 不做新的可视化大屏。

轮询可以继续沿用已有刷新逻辑；如果需要新增轮询，必须保持轻量，并在 plan 中明确停止条件。

## 8. 测试策略

### 8.1 后端测试

必须优先写后端测试，再实现。

建议覆盖：

- Celery task 注册到 `celery_app.conf.imports`。
- eager mode 下 `run_rag_ingestion_task.delay(task_id).get()` 能执行成功。
- 上传接口创建任务后能投递 Celery task。
- eager mode 下上传小 txt/md 文件最终写出 `RagDocument`。
- worker mode 或 fake dispatch 下上传接口可以返回 queued/pending，而不是阻塞等待。
- task 执行时会从数据库读取 `RagIngestionTask`，而不是依赖内存态对象。
- task 成功写回 `status=succeeded`、`progress=100`、`document_id`、`result_json`。
- task 失败写回 `status=failed`、`error_message`、`can_retry`。
- retry 接口复用 Celery dispatch，不再复制同步入库逻辑。
- 非 owner 不能查看或 retry 别人的任务。
- Celery dispatch 失败时任务状态可观测。

### 8.2 前端测试

只做最小必要测试：

- 知识库页能显示 queued/running/succeeded/failed 文案。
- 上传成功但任务未完成时，不要求文档立即出现在列表。
- retry 后显示任务处理中。
- 管理员后台 ingestion 监控能显示 queued/running 指标或文案。

### 8.3 回归验证

必须运行：

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

浏览器验证：

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

要求：

- 桌面端无明显布局错乱。
- 移动端无横向溢出。
- 页面无可见 `undefined`。
- 上传/任务状态展示文案不误导用户。

## 9. 非目标

本阶段明确不做：

- 不做 OCR。
- 不做 Word / Excel / 网页解析。
- 不接 Qdrant、pgvector、对象存储。
- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不重构 RAG 检索、rerank、evaluation 算法。
- 不重构 Agent 或 LangGraph 主链路。
- 不把全部 AI 任务都迁移到 Celery。
- 不引入 WebSocket / SSE 实时推送。
- 不强制本地安装 Redis 或 PostgreSQL。
- 不要求真实启动 Celery worker 才能跑测试。

## 10. 验收标准

完成后必须满足：

- active plan 所有任务完成。
- `backend_python/tasks/rag_ingestion.py` 或等价 task 模块存在。
- Celery app 注册 RAG ingestion task。
- 上传接口和 retry 接口通过 Celery dispatch 进入任务执行逻辑。
- eager mode 下测试可同步执行完整摄取链路。
- worker mode 下接口可返回任务已排队状态，不阻塞等待完整入库。
- `RagIngestionTask` 状态、进度、失败原因、重试次数、document_id 和 result_json 写回正确。
- 用户侧和管理员侧现有 ingestion task 页面保持可用。
- 后端测试、前端测试、前端构建通过。
- 内置浏览器验证知识库页和管理员后台桌面/移动端通过。
- spec 和追求目标生成的 plan 最终归档到 completed。
- `docs/project-baseline.md`、`docs/roadmap/current-state.md`、`docs/specs/README.md`、`docs/plans/README.md` 更新。

## 11. 追求目标执行约定

本阶段可以直接交给 Codex 追求目标模式执行。执行时不需要当前对话先写 implementation plan，而是要求追求目标模式先根据本 spec 在 `docs/plans/active/` 下生成 plan，再严格按 plan 执行。

执行时必须遵守：

- 每轮开发前先用中文解释本轮要学的异步任务 / RAG 工程化知识点。
- 优先测试驱动，先写或更新后端测试，再实现。
- 当前阶段优先改 `backend_python` 下的 RAG ingestion、Celery task、routes 和测试。
- 前端只做最小化状态文案和任务展示兼容。
- 不做 Docker/Nginx/VPS/HTTPS 上线。
- 不引入 Qdrant、pgvector、对象存储。
- 不重构 RAG 检索、Agent、LangGraph 或 Vue3 主链路。
- 完成后运行后端全量测试、前端全量测试、前端构建和浏览器验证。
- 完成后归档 spec/plan 并更新路线文档。

## 12. 面试表达种子

可以这样讲：

```text
我没有让 RAG 文档上传接口长期承担所有耗时逻辑，而是把文档摄取改成异步任务链路。HTTP 接口负责鉴权、校验、创建 RagIngestionTask 并投递 Celery task；Celery task 只拿 taskId，再从数据库读取任务输入快照，执行文本解析、清洗、chunk 入库，并把状态、进度、失败原因和 documentId 写回数据库。

本地测试环境使用 Celery eager mode，不需要真实 Redis 和 worker 也能验证完整任务链路；生产环境可以切换到 Redis broker 和 Celery worker。这样既保证本地开发简单，又让 RAG 入库具备任务状态、失败重试和管理员观测能力。
```

