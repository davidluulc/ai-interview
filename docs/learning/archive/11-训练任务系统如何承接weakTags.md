# 11 训练任务系统如何承接 weakTags

## 1. weakTags 的局限

`weakTags` 是报告里的薄弱点标签。

例如：

```json
{
  "weakTags": ["rag_quality", "agent_state"]
}
```

它能说明：

```text
用户哪里薄弱。
```

但它不能说明：

```text
用户今天应该练什么？
这个薄弱点练了几次？
有没有进步？
是否已经可以归档？
下一轮面试是否还要继续追问？
```

所以 `weakTags` 更像诊断结果，不是训练过程本身。

## 2. TrainingTask 解决什么问题

`TrainingTask` 是把薄弱点变成可跟踪任务。

它保存：

- `weak_tag`：薄弱点标签。
- `weak_label`：中文名称。
- `title`：训练任务标题。
- `description`：训练任务说明。
- `status`：任务状态。
- `priority`：优先级。
- `mastery_score`：掌握度。
- `attempt_count`：训练次数。
- `metadata_json`：来源报告、模板摘要等扩展信息。

这样系统就能从：

```text
你在 rag_quality 上薄弱。
```

升级为：

```text
你有一个 RAG 质量评估专项训练任务，当前掌握度 45，优先级 high，还没有完成。
```

## 3. 去重规则为什么重要

如果每次报告都生成一条新任务，很快会出现大量重复任务。

例如用户连续三次在 `rag_quality` 上薄弱，如果没有去重，会变成：

```text
RAG 质量评估任务 1
RAG 质量评估任务 2
RAG 质量评估任务 3
```

这会让用户不知道该练哪一个。

当前规则是：

```text
同一个用户、同一个求职档案、同一个 weakTag，如果已有未归档任务，就更新原任务。
如果没有活跃任务，再新建任务。
```

这样既能保留训练目标，又不会堆出重复任务。

## 4. mastery_score 为什么先用规则评分

第一版掌握度不用大模型直接打分，而是使用规则：

```text
不会：-5
模糊：+8
完整：+15
```

并限制在：

```text
0 <= mastery_score <= 100
```

原因是：

- 规则可解释。
- 测试稳定。
- 不依赖模型波动。
- 面试时能讲清楚。

后续可以把模型评分作为辅助信号，但不应该完全依赖模型黑箱判断。

## 5. 关键代码位置

训练任务数据模型：

```text
backend_python/db_models.py
```

SQLite 兼容建表：

```text
backend_python/database.py
```

训练任务业务逻辑：

```text
backend_python/training_tasks.py
```

训练任务 API：

```text
backend_python/routes/training.py
```

路由注册：

```text
backend_python/main.py
```

测试：

```text
tests/test_training_tasks.py
tests/test_training_task_generation.py
```

## 6. 面试时怎么讲

可以这样说：

```text
原来系统在报告里能生成 weakTags，但 weakTags 只是薄弱点标签，不能记录训练过程。所以我新增了 TrainingTask，把 weakTag 转成可跟踪任务，记录任务状态、优先级、掌握度和训练次数。

生成任务时我做了去重：同一个用户、同一个求职档案、同一个 weakTag，如果已有未归档任务，就更新原任务，避免重复堆任务。掌握度第一版采用规则评分，比如回答完整加 15 分，答不上来扣 5 分，并限制在 0 到 100，保证可解释和可测试。
```

## 7. 当前边界

当前已经完成：

- `TrainingTask` 数据模型。
- SQLite 兼容建表。
- 训练任务 service。
- 从报告 weakTags 生成训练任务。
- 同 weakTag 活跃任务去重。
- 开始、完成、归档任务接口。
- 掌握度规则更新。
- 用户任务隔离。

当前还没有完成：

- 前端训练中心页面。
- 训练任务影响 Agent 决策。
- 每次训练回答明细表。
- 掌握度趋势图。
- 管理员后台查看训练任务。

这些会在后续阶段继续推进。

