# Vue3 知识库页面产品化 V1 设计文档

更新时间：2026-06-13

## 1. 阶段定位

本阶段目标是把 Vue3 前端里的知识库页面从占位页升级为真实可用的 RAG 知识库工作台。

当前项目后端已经具备较完整的 RAG 工程能力：

- 三类知识库：岗位知识库、题库、候选人画像。
- RAG 文档管理接口。
- 文档生命周期：enabled / disabled / archived。
- 文档可见性：private / public。
- chunk 切分、hash、去重统计。
- BM25、向量检索、hybrid search、rerank、query rewrite。
- RAG debug、命中日志、命中解释和质量评估。

但 Vue3 前端的 `KnowledgePage.vue` 目前仍是占位页，用户无法在 Vue3 入口里完成知识库文档录入、查看、筛选、状态管理和检索解释。因此本阶段只做“已有 RAG 能力的 Vue3 产品化承接”，不重新开发 RAG 算法。

## 2. 用户目标

目标用户仍然是大学生、求职者和项目演示者。

他们进入知识库页面时，应该能回答四个问题：

1. 我现在有哪些知识库资料？
2. 这些资料分别属于岗位知识库、题库，还是候选人画像？
3. 哪些资料正在参与检索，哪些被禁用或归档？
4. 系统为什么根据这些资料生成某个面试问题？

本阶段要让知识库页面从“开发调试入口”变成“AI 面试系统的资料管理和 RAG 可解释入口”。

## 3. 本阶段范围

### 3.1 要做

1. Vue3 知识库文档列表
   - 调用 `GET /api/rag/documents` 读取当前用户的 RAG 文档。
   - 展示标题、知识库类型、状态、可见性、sourceType、chunk 数、重复 chunk 数、更新时间。
   - 支持空状态、加载状态、错误状态。

2. Vue3 知识库筛选
   - 按知识库类型筛选：全部、岗位知识库、题库、候选人画像。
   - 按状态筛选：全部、enabled、disabled、archived。
   - 按可见性筛选：全部、private、public。
   - 按标题关键词搜索。

3. Vue3 文档创建入口
   - 支持手动录入标题、知识库类型、内容、可见性和 metadata。
   - metadata 当前阶段采用简单 JSON 文本框，提交前做前端 JSON 校验。
   - 创建成功后刷新列表。

4. Vue3 文档详情
   - 调用 `GET /api/rag/documents/{document_id}`。
   - 展示文档基本信息。
   - 展示 chunk 列表：chunkIndex、content、contentHash、metadata。
   - chunk 内容需要可折叠或限制高度，避免页面被长文本撑爆。

5. Vue3 文档状态管理
   - 调用 `PATCH /api/rag/documents/{document_id}/status`。
   - 支持启用、禁用、归档。
   - 删除使用 `DELETE /api/rag/documents/{document_id}`，但必须有二次确认。
   - 普通用户只管理自己的文档。

6. Vue3 RAG debug / 命中解释入口
   - 复用 `GET /api/rag/debug`。
   - 用户输入角色、岗位标签、简历摘要、JD、面试阶段。
   - 页面展示三类召回结果：岗位知识库、题库、候选人画像。
   - 展示 quality 和 explanations，让用户知道命中质量和系统解释。

7. 前端 API 与状态管理
   - 新增 `frontend/src/api/knowledge.ts`。
   - 新增 `frontend/src/stores/knowledge.ts`。
   - 页面优先消费 store，不在组件里散落复杂请求逻辑。

8. 前端测试
   - 先写或更新前端测试，再实现。
   - 覆盖 API client、Pinia store、KnowledgePage 关键渲染和交互。

9. 中文学习文档
   - 新增一篇学习文档，讲清楚“Vue3 知识库页面如何承接 RAG 工程能力”。

### 3.2 不做

本阶段明确不做：

- 不重写 RAG 检索算法。
- 不新增 OCR、Word、Excel、网页解析。
- 不新增 Qdrant、pgvector 或外部向量数据库。
- 不引入 LangGraph。
- 不改 Agent 主流程。
- 不做管理员后台 V2。
- 不做 Docker、Nginx、VPS、HTTPS 上线。
- 不把知识库页面做成复杂 CMS。
- 不引入 React、Vue 以外的新前端框架。

如果发现后端接口字段不够前端展示，允许做极小范围兼容增强，但必须先写后端测试，并且不得破坏现有接口。

## 4. 页面信息架构

知识库页面建议分为四块。

### 4.1 页面头部

展示：

- 页面标题：知识库。
- 一句话说明：管理参与 RAG 检索的岗位资料、题库资料和候选人画像资料。
- 一个主要动作：新增文档。

说明文字要面向用户，不要写成纯技术调试描述。

### 4.2 文档管理区

核心列表字段：

```text
标题
知识库类型
状态
可见性
sourceType
chunk 数
重复 chunk 数
更新时间
操作
```

知识库类型中文映射：

```text
role_knowledge -> 岗位知识库
question_bank -> 题库
candidate_memory -> 候选人画像
```

状态中文映射：

```text
enabled -> 启用中
disabled -> 已禁用
archived -> 已归档
```

可见性中文映射：

```text
private -> 仅自己可用
public -> 公共资料
```

操作：

- 查看详情。
- 启用。
- 禁用。
- 归档。
- 删除。

### 4.3 新增文档表单

字段：

```text
title
knowledgeBase
sourceType
visibility
content
metadataJson
```

前端校验规则：

- title 不能为空。
- content 不能为空。
- knowledgeBase 必须是三类之一。
- visibility 必须是 private 或 public。
- metadataJson 为空时按 `{}` 处理。
- metadataJson 不为空时必须能被 `JSON.parse()` 解析成对象。

失败提示要说人话，例如：

```text
metadata 必须是合法 JSON 对象，例如 {"role":"Python 后端","level":"实习"}。
```

### 4.4 RAG 调试与解释区

这一块不是给普通用户看底层日志，而是给项目演示和学习使用。

输入字段：

```text
candidateName
role
positionTag
resume
jd
stage
```

输出字段：

```text
roleKnowledge hits
questionBank hits
candidateMemory hits
quality
explanations
```

页面表达建议：

- “岗位知识库命中”。
- “题库命中”。
- “候选人画像命中”。
- “召回质量”。
- “为什么这些资料会进入面试上下文”。

不要把原始 JSON 大面积直接塞在页面首屏。原始 JSON 可以放到可折叠区域。

## 5. 数据流设计

### 5.1 文档列表数据流

```text
KnowledgePage mounted
-> knowledge store loadDocuments()
-> GET /api/rag/documents
-> store 保存 documents
-> computed 根据筛选条件生成 filteredDocuments
-> 页面渲染列表、空状态或错误状态
```

### 5.2 新增文档数据流

```text
用户填写表单
-> 前端校验 title/content/metadataJson
-> POST /api/rag/documents
-> 创建成功
-> store 重新 loadDocuments()
-> 表单清空或收起
```

### 5.3 文档详情数据流

```text
用户点击查看详情
-> GET /api/rag/documents/{id}
-> store 保存 selectedDocumentDetail
-> 页面展示 document 和 chunks
```

### 5.4 状态管理数据流

```text
用户点击禁用/启用/归档
-> PATCH /api/rag/documents/{id}/status
-> 更新成功
-> 替换列表中的对应文档或重新 loadDocuments()
```

### 5.5 RAG debug 数据流

```text
用户填写调试条件
-> GET /api/rag/debug
-> 页面展示三类 hits、quality、explanations
-> 用户可以理解系统下一轮面试会参考哪些资料
```

## 6. 前端模块设计

### 6.1 API 模块

新增：

```text
frontend/src/api/knowledge.ts
```

职责：

- 定义 RAG 文档、chunk、debug 响应类型。
- 封装 `fetchRagDocuments()`。
- 封装 `createRagDocument()`。
- 封装 `fetchRagDocumentDetail()`。
- 封装 `updateRagDocumentStatus()`。
- 封装 `deleteRagDocument()`。
- 封装 `debugRagContext()`。

### 6.2 Store 模块

新增：

```text
frontend/src/stores/knowledge.ts
```

职责：

- 保存 documents。
- 保存 selectedDocumentDetail。
- 保存 debugResult。
- 保存 loading、saving、error。
- 保存筛选条件。
- 提供 filteredDocuments。
- 提供 create/update/delete/debug 动作。

### 6.3 页面模块

修改：

```text
frontend/src/pages/app/KnowledgePage.vue
```

职责：

- 编排页面结构。
- 调用 knowledge store。
- 不直接散落复杂 fetch。
- 处理表单、筛选、详情、debug 区域展示。

如果 `KnowledgePage.vue` 过大，可以拆组件，但本阶段优先控制范围。只有当页面超过明显可维护边界时，再考虑拆：

```text
frontend/src/components/knowledge/KnowledgeDocumentList.vue
frontend/src/components/knowledge/KnowledgeDocumentForm.vue
frontend/src/components/knowledge/RagDebugPanel.vue
```

## 7. 测试计划

### 7.1 API 测试

建议新增：

```text
frontend/src/api/knowledge.test.ts
```

覆盖：

- `fetchRagDocuments()` 调用 `/api/rag/documents`。
- `createRagDocument()` 提交 JSON payload。
- `fetchRagDocumentDetail()` 调用详情接口。
- `updateRagDocumentStatus()` 调用状态接口。
- `deleteRagDocument()` 调用删除接口。
- `debugRagContext()` 正确拼接 query params。

### 7.2 Store 测试

建议新增：

```text
frontend/src/stores/knowledge.test.ts
```

覆盖：

- 加载文档成功。
- 加载失败写入 error。
- 按知识库类型筛选。
- 按状态筛选。
- 按可见性筛选。
- 按标题搜索。
- metadata JSON 校验失败时不提交。
- 创建成功后刷新列表。
- 更新状态成功后刷新或更新列表。
- 删除成功后二次刷新或移除列表项。

### 7.3 页面测试

建议新增：

```text
frontend/src/pages/app/knowledge-page.test.ts
```

覆盖：

- 页面渲染标题和主要入口。
- 文档列表显示中文知识库类型、状态、可见性。
- 空状态显示引导。
- 点击新增文档能展示表单。
- metadata JSON 错误时显示提示。
- 点击详情能展示 chunks。
- debug 区域能展示三类召回结果。

### 7.4 浏览器验证

完成后用内置浏览器验证：

```text
http://127.0.0.1:5173/vue/app/knowledge
```

验证范围：

- 桌面端。
- 移动端 390px 左右。
- 登录态。
- 文档列表。
- 新增文档。
- 查看详情。
- 启用 / 禁用 / 归档。
- RAG debug 结果展示。
- 页面无明显横向溢出。
- 页面不出现 `undefined`。

## 8. 验收标准

本阶段完成后，应满足：

1. 用户能在 Vue3 知识库页看到自己的 RAG 文档。
2. 用户能按知识库类型、状态、可见性和标题搜索文档。
3. 用户能新增手动文档，且 metadata JSON 校验清晰。
4. 用户能查看文档详情和 chunks。
5. 用户能启用、禁用、归档和删除自己的文档。
6. 用户能在页面里运行 RAG debug，并看到三类 RAG 命中和解释。
7. 页面表达从“接口调试”升级为“知识库管理和 RAG 可解释工作台”。
8. 前端测试通过。
9. 前端构建通过。
10. 内置浏览器桌面端和移动端验证通过。

## 9. 面试表达目标

本阶段完成后，项目可以这样讲：

```text
我的系统不是只把 RAG 写在后端，而是做了知识库管理页面。
用户可以把资料按岗位知识库、题库、候选人画像三类录入系统，并管理文档的启用、禁用、归档和可见性。
每份文档入库后会被切成 chunks，后续面试 Agent 会通过 RAG 检索这些 chunks。
为了避免 RAG 变成黑箱，我还做了 debug 和命中解释入口，可以看到三类 RAG 分别命中了什么、召回质量如何、为什么这些资料会进入下一轮面试上下文。
```

如果面试官追问工程实现，可以补充：

```text
前端使用 Vue3 + Pinia + API client 分层实现。
API client 只负责 HTTP 请求，store 负责文档列表、筛选、详情、debug 结果和加载错误状态，页面组件只负责展示和交互编排。
后端继续复用 FastAPI 的 RAG 文档接口，保证前端产品化不破坏已有 RAG 检索链路。
```

## 10. 风险与边界

主要风险：

- 页面一次性承载列表、表单、详情和 debug，可能变得臃肿。
- RAG debug 返回字段较多，直接展示 JSON 会让页面难看。
- 删除文档是破坏性操作，必须二次确认。
- metadata JSON 对新手不友好，需要给出示例。

处理策略：

- 优先通过分区和折叠控制复杂度。
- 首屏展示摘要，原始 JSON 放在可折叠区域。
- 删除动作必须确认。
- metadata 提供默认示例和错误提示。
- 如果页面明显过大，再拆 knowledge components，不提前过度拆分。

## 11. 后续阶段预留

本阶段完成后，后续可以继续推进：

1. 知识库批量导入和文件上传。
2. OCR、Word、Excel、网页解析。
3. 异步入库任务队列和入库进度。
4. Qdrant / pgvector 持久化向量数据库。
5. 管理员后台 RAG 文档审核和质量监控 V2。
6. LangGraph checkpoint 持久化和 human-in-the-loop。
7. 真实 VPS、域名、HTTPS 上线。

这些内容不进入本阶段实现范围。
