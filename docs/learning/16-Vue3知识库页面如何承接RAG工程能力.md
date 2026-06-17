# Vue3 知识库页面如何承接 RAG 工程能力

更新时间：2026-06-13

## 1. 这一阶段到底做了什么

这一阶段不是重新开发 RAG 算法，而是把后端已经具备的 RAG 工程能力，通过 Vue3 前端做成一个用户能理解、能操作、能排查问题的知识库工作台。

后端已经有：

- RAG 文档接口。
- 三类知识库。
- 文档状态和可见性。
- chunk 切分结果。
- RAG debug。
- 命中质量和解释。

但是如果前端只是一个占位页，面试官和用户都很难感受到这些能力真的被产品化了。所以这一阶段的重点是把“后端能力”翻译成“产品页面”。

## 2. 为什么知识库页面不是重新做 RAG

RAG 的核心链路通常包括：

```text
文档入库
-> 文本切分 chunk
-> 建索引
-> 检索
-> rerank
-> 拼上下文
-> 交给 LLM
```

这些能力主要属于后端和算法工程。

知识库页面主要解决的是另一类问题：

```text
用户怎么录入资料
用户怎么知道资料属于哪个知识库
用户怎么知道资料有没有参与检索
用户怎么看到 chunk 和命中解释
用户怎么排查为什么模型问了某个问题
```

所以这一阶段的工程重点不是“让检索更强”，而是“让已有检索能力可管理、可观察、可解释”。

## 3. 三层前端结构怎么理解

这一阶段用了三层结构：

```text
API client
-> Pinia store
-> Vue Page
```

### 3.1 API client

文件：

```text
frontend/src/api/knowledge.ts
```

它只负责和后端接口通信。

比如：

- `fetchRagDocuments()` 调用文档列表接口。
- `createRagDocument()` 创建文档。
- `fetchRagDocumentDetail()` 查看文档和 chunks。
- `updateRagDocumentStatus()` 修改状态。
- `deleteRagDocument()` 删除文档。
- `debugRagContext()` 调用 RAG debug。

API client 不负责页面展示，也不负责复杂业务状态。这样做的好处是：以后后端接口路径变了，只需要优先改 API client，不用到页面里到处找 fetch。

### 3.2 Pinia store

文件：

```text
frontend/src/stores/knowledge.ts
```

store 负责把接口返回的数据整理成页面可以直接使用的状态。

它保存：

- `documents`：原始文档列表。
- `filteredDocuments`：筛选后的文档列表。
- `selectedDetail`：当前查看的文档详情和 chunks。
- `debugResult`：RAG debug 结果。
- `loading` / `saving` / `error`：加载、保存和错误状态。
- `metadataError`：metadata JSON 校验错误。

你可以把 store 理解成前端的“业务状态中枢”。页面不需要知道具体请求怎么发，只需要调用 `loadDocuments()`、`runDebug()` 这些动作。

### 3.3 Vue Page

文件：

```text
frontend/src/pages/app/KnowledgePage.vue
```

页面负责把状态展示给用户，并处理点击、输入、筛选、提交这些交互。

它展示：

- 文档总数、启用数量、归档数量。
- 文档列表。
- 新增文档表单。
- 文档详情和 chunks。
- RAG debug 表单。
- 三类 RAG 命中结果。

页面不直接散落复杂请求逻辑，这样它会更像产品页面，而不是接口测试工具。

## 4. 三类知识库怎么对应业务

系统里有三类知识库：

```text
role_knowledge -> 岗位知识库
question_bank -> 题库
candidate_memory -> 候选人画像
```

岗位知识库放岗位相关的技术栈、业务背景、岗位要求。

题库放面试题、追问模板、考察点。

候选人画像放用户简历、项目经历、历史回答、薄弱点等个人相关信息。

面试 Agent 生成问题时，不应该只凭空问，而是应该结合这三类资料：

```text
岗位知识库告诉系统“这个岗位应该考什么”
题库告诉系统“可以怎样问”
候选人画像告诉系统“这个人哪里需要深挖”
```

这就是为什么知识库页面要把三类资料明确展示出来。

## 5. status、visibility、metadata、chunk 为什么重要

### 5.1 status

`status` 表示文档生命周期。

```text
enabled -> 启用中
disabled -> 已禁用
archived -> 已归档
```

它解决的是“哪些资料应该参与检索”的问题。

比如某份题库资料质量不好，可以先 disabled，而不是直接删除。

### 5.2 visibility

`visibility` 表示文档可见性。

```text
private -> 仅自己可用
public -> 公共资料
```

它解决的是权限边界问题。

真实产品里，用户自己的简历和回答肯定不能被其他用户检索到。

### 5.3 metadata

`metadata` 是文档的结构化补充信息。

例如：

```json
{
  "role": "Python 后端",
  "level": "实习",
  "difficulty": "medium"
}
```

它的价值是后续可以做 metadata filter。

比如只检索“Python 后端 + 实习 + medium 难度”的题库内容。

### 5.4 chunk

chunk 是文档被切分后的检索单元。

大模型不能直接把所有资料都塞进 prompt，所以 RAG 通常会先把文档切成一小段一小段，再根据用户问题检索最相关的 chunk。

所以查看 chunks 可以帮助排查：

- 文档有没有被正确切分。
- chunk 内容是否过长或过短。
- metadata 是否跟着 chunk 进入检索。
- 重复 chunk 是否太多。

## 6. RAG debug 区域有什么用

RAG debug 不是给普通用户天天使用的主功能，它更像项目演示和调试入口。

它能展示：

- 岗位知识库命中了什么。
- 题库命中了什么。
- 候选人画像命中了什么。
- 命中质量如何。
- 系统为什么把这些资料放进上下文。

这能解决一个很重要的问题：

```text
AI 为什么这么问？
```

如果没有 debug 和解释，系统就很容易变成黑箱。

## 7. 面试时可以怎么讲

可以这样讲：

```text
我的 AI 模拟面试系统不只是后端写了 RAG 检索，还做了知识库管理页面。
用户可以把资料按岗位知识库、题库、候选人画像三类录入系统，并管理文档的启用、禁用、归档和可见性。
每份文档入库后会被切成 chunks，后续 Agent 会通过 RAG 检索这些 chunks 来生成更贴合岗位和候选人的面试问题。
为了避免 RAG 变成黑箱，我还做了 RAG debug 和命中解释入口，可以看到三类 RAG 分别命中了什么，以及为什么这些资料会进入面试上下文。
```

如果面试官追问前端工程实现，可以说：

```text
前端采用 Vue3 + Pinia + API client 分层。
API client 只封装 HTTP 请求，store 管理文档列表、筛选条件、详情、debug 结果和错误状态，页面组件负责展示和交互。
这样页面不会直接散落请求逻辑，后续扩展文件上传、异步入库或更复杂筛选时，也比较容易维护。
```

## 8. 你需要重点理解的知识点

你不用一口气记住所有代码，但要理解这些关键词：

- API client：封装请求。
- Pinia store：管理前端业务状态。
- RAG 文档：知识库里的原始资料。
- chunk：真正参与检索的小段文本。
- metadata：用于过滤和解释的结构化信息。
- status：文档生命周期控制。
- visibility：权限边界。
- debug：可观测性入口。

这些词能串起来，你讲项目时就不会只停留在“我调了一个大模型接口”。
