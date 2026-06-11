# LangGraph checkpoint 和 thread state 怎么理解

## 1. 一句话理解

checkpoint 是 LangGraph 在某个 `threadId` 维度下保存的图状态快照。thread state 是当前图运行时携带的状态数据。普通数据库记录是业务持久化数据。`AgentDecisionLog` 是为了排查 Agent 决策而记录的可观测日志。

## 2. 为什么 AI 模拟面试需要 threadId

同一个用户可以有多场面试，同一场面试又有多轮问答。`threadId` 用来标识“同一条 LangGraph 实验流程”，让 checkpoint 知道这几轮状态属于同一场实验。

在当前项目里，`threadId` 主要服务于旁路 LangGraph V2 接口：

```text
POST /api/langgraph-agent/next-question-v2
GET  /api/langgraph-agent/checkpoint/{thread_id}
```

也就是说，主面试流程仍然走 `/api/interview/next-question`，LangGraph V2 先作为实验工作流验证状态编排、工具调用、决策适配和 checkpoint 能力。

## 3. checkpoint 和数据库记录的区别

checkpoint 偏运行时恢复和调试，数据库记录偏业务事实保存。

举个例子：

- 面试历史记录：用户完成了一场面试，报告和问答内容要长期保存，这是业务数据。
- RAG 命中日志：系统某次检索命中了哪些 chunk，这是可观测日志。
- Agent 决策日志：Agent 为什么降低难度、切换话题或继续深挖，这是决策日志。
- LangGraph checkpoint：某个 `threadId` 的图运行到某一步时，图状态是什么，这是工作流状态快照。

当前 V2 使用的是 `MemorySaver`，它是内存版 checkpoint，服务重启会丢失。它适合证明 checkpoint 概念，但不等于生产级持久化。

## 4. checkpoint 和 AgentDecisionLog 的区别

checkpoint 保存图状态，方便恢复和继续跑图。`AgentDecisionLog` 保存 Agent 为什么这么决策，方便排查黑箱问题。

两者可以互补：

```text
checkpoint 关注：图运行到了哪里，state 里有什么。
AgentDecisionLog 关注：Agent 看到了什么状态，为什么选择这个 action。
```

如果未来继续升级，可以把 checkpoint 持久化到 SQLite、PostgreSQL 或专门的 LangGraph checkpoint store，同时继续保留 `AgentDecisionLog` 做业务可观测性。

## 5. 当前项目怎么落地

当前 LangGraph V2 做了这些事：

- 保留自研 Agent 主流程。
- 保留 V1 POC 接口。
- 新增 V2 旁路接口。
- 用 adapter 接入真实或 fake RAG。
- 用 adapter 接入真实或 fake Agent decision。
- 用 `threadId` 调用 LangGraph。
- 返回 `checkpointSummary`、`nodeTrace`、`toolCalls` 和 `decision`。

当前 V2 的边界也很清楚：

- 不替换主面试接口。
- 不做完整 human-in-the-loop。
- 不做生产级 checkpoint 持久化。
- 不做 Docker / Nginx / 云服务器上线。

## 6. 面试表达

可以这样讲：

```text
我先保留自研 Agent 主流程，再用 LangGraph V2 做旁路验证。V2 通过 adapter 接入真实 RAG 和真实 Agent 决策，并用 threadId + MemorySaver 演示 checkpoint。这样既控制风险，又能证明项目具备迁移到标准 Agent 工作流框架的能力。
```

如果面试官继续追问“MemorySaver 是不是生产级方案”，可以这样答：

```text
不是。MemorySaver 是进程内存级别的 checkpoint，服务重启会丢失。我在项目里先用它验证 threadId、graph state 和 checkpoint 的工作方式。生产环境会进一步切换到 SQLite 或 PostgreSQL checkpoint，并和 AgentDecisionLog、面试历史记录做边界划分。
```
