# Celery Worker Readiness：RAG 异步任务运行说明

## 为什么需要 Worker

RAG 文档上传、文本解析、清洗、切 chunk 和入库是慢任务。HTTP 接口应该快速返回 taskId，后台 Celery worker 继续处理任务，前端和管理员后台通过任务状态观察进度。

## 三种运行模式

### local/eager

用于本地开发和自动化测试。`CELERY_TASK_ALWAYS_EAGER=true` 时任务在当前进程内同步执行，不需要 Redis 或外部 worker。

### fallback

Redis 或 Celery 不可用时，系统应返回可解释的失败或降级状态，不暴露密钥，不让任务静默丢失。

### worker

用于生产或部署演练。`CELERY_TASK_ALWAYS_EAGER=false`，FastAPI 把任务派发到 Redis broker，Celery worker 从队列消费并执行。

## Windows 本地启动示例

```powershell
set CELERY_TASK_ALWAYS_EAGER=false
set CELERY_BROKER_URL=redis://localhost:6379/1
set CELERY_RESULT_BACKEND=redis://localhost:6379/2
scripts\start-celery-worker.cmd
```

## 面试表达

我没有把文件解析和 chunk 入库放在 HTTP 请求里长时间阻塞，而是把它设计为异步任务。上传接口返回 taskId，任务状态记录 pending、queued、running、succeeded、failed，失败后可以基于 textSnapshot retry，管理员后台能看到任务健康状态和失败原因。
