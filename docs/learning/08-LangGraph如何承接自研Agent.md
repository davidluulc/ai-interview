# LangGraph 如何承接自研 Agent

## 1. 为什么先做自研 Agent

本项目先做自研 Interview Orchestrator Agent，是为了把 Agent 的底层机制学清楚：

- State：当前面试看到了什么。
- Tool：三类 RAG 怎样被调用。
- Decision：为什么降难度、深挖、换话题或结束。
- Trace：每个节点做了什么。
- Guardrail：模型输出不稳定时怎样兜底。

如果一开始直接用框架，容易只会调用框架 API，却讲不清 Agent 的状态和决策。

## 2. LangGraph POC 做了什么

LangGraph POC 没有替换主流程，而是新增旁路实验链路：

```text
observe_state
-> analyze_answer
-> retrieve_context
-> select_action
-> generate_question
-> update_memory
```

这个链路证明：现有自研 Agent 的节点可以映射成 LangGraph StateGraph。

## 3. StateGraph 怎么理解

可以把 StateGraph 理解成“带状态的流程图”：

- State 是整场流程共享的数据包。
- Node 是每一步处理逻辑。
- Edge 是节点之间的流转顺序。
- compile 是把设计好的图变成可运行对象。

## 4. 为什么是旁路 POC

主流程继续使用自研 Agent，保证面试功能稳定。

LangGraph POC 只用于验证迁移方向。这样就算 POC 有问题，也不会影响用户正常模拟面试。

## 5. checkpoint 和 human-in-the-loop 为什么先不做

checkpoint 可以保存图状态，human-in-the-loop 可以让流程暂停等待人工输入。它们都很重要，但第一版 POC 先证明节点链路能跑通。

后续可以继续升级：

```text
保存每轮 graph state
-> 中断后恢复面试
-> 人工确认是否继续深挖
-> 把 Agent 调试路径做成可视化
```

## 6. 面试时怎么讲

可以这样说：

> 我先自研了一个 Interview Orchestrator Agent，用它管理 state、toolCalls、decision、trace 和 fallback。后续我又做了 LangGraph POC，把自研 Agent 的 observe_state、analyze_answer、retrieve_context、select_action、generate_question、update_memory 映射成 StateGraph 节点。这个 POC 不替换主流程，而是验证项目未来可以迁移到更标准的 Agent 工作流框架。
