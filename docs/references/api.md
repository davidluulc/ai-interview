# 接口文档

本文档说明 Python FastAPI 后端目前提供的接口。

基础地址：

```text
http://localhost:8000
```

## POST /api/interview/next-question

生成下一道面试题。

这个接口用于“动态追问”。前端不会一次性生成全部题目，而是每次把候选人信息、历史回答和下一阶段发给后端，让模型生成下一题。

### 请求示例

```json
{
  "profile": {
    "candidateName": "张同学",
    "targetRole": "AI 应用开发实习生",
    "applicationType": "实习投递",
    "resume": "候选人的简历摘要",
    "jd": "目标岗位 JD",
    "company": "公司或岗位要求",
    "mode": "综合面试",
    "depth": "standard"
  },
  "history": [
    {
      "stage": "自我介绍",
      "question": "请你先做一个 1 分钟左右的自我介绍。",
      "answer": "我的回答..."
    }
  ],
  "nextStage": "项目背景"
}
```

### 返回示例

```json
{
  "stage": "项目背景",
  "stability": "自然追问",
  "prompt": "你刚才提到了某项目，请说明项目的业务背景和目标用户。"
}
```

### 设计说明

- 前端负责收集用户信息和历史回答。
- 后端负责组织 prompt 并调用模型。
- API key 保存在后端，不能暴露到前端。
- 后端要求模型返回 JSON，方便前端渲染。
- 如果模型接口失败，前端会使用本地兜底问题。

## POST /api/interview/report

生成最终面试报告。

这个接口会根据候选人信息和本轮问答记录，生成评分、优势、风险点和下一步训练建议。

### 请求示例

```json
{
  "profile": {
    "candidateName": "张同学",
    "targetRole": "AI 应用开发实习生"
  },
  "answers": [
    {
      "stage": "技术基础",
      "question": "请解释你熟悉的一个核心技术点。",
      "answer": "我的回答..."
    }
  ]
}
```

### 返回示例

```json
{
  "score": 75,
  "strengths": ["回答能结合项目经历"],
  "risks": ["技术原理解释还不够深入"],
  "actions": ["用 STAR 结构重写项目经历"]
}
```

### 设计说明

- 报告生成使用较低的 temperature，让评分更稳定。
- 模型返回结构化 JSON，前端直接渲染成报告卡片。
- 前端会把报告和问答记录保存到历史复盘中。

## POST /api/resume/parse

解析简历文件。

这个接口用于上传 PDF 或图片简历，把简历内容转成面试官可以使用的简历摘要。

### 请求方式

表单上传：

```text
resume=<PDF 或图片文件>
```

当前支持：

- PDF
- PNG
- JPG / JPEG
- WebP

### 返回示例

```json
{
  "fileName": "resume.pdf",
  "fileType": "application/pdf",
  "summary": "解析后的简历摘要..."
}
```

### 设计说明

- PDF 简历用 `pypdf` 在后端本地解析。
- 图片简历调用视觉模型解析。
- MVP 阶段不保存用户上传的原始文件。
- 解析结果会填入简历摘要，作为后续面试追问上下文。

## 前端兜底机制

前端有本地兜底逻辑：

- 模型生成问题失败时，使用本地问题模板。
- 模型生成报告失败时，使用本地报告估算逻辑。

这样即使模型接口异常，用户也可以完成一轮模拟面试。

## GET /api/history

读取最近 20 条历史面试记录。

### 返回示例

```json
[
  {
    "id": 1,
    "createdAt": "2026-05-28T18:20:00",
    "profile": {
      "candidateName": "张同学",
      "targetRole": "AI 应用开发实习生"
    },
    "answers": [],
    "report": {
      "score": 75
    }
  }
]
```

## POST /api/history

保存一条面试记录。

### 请求示例

```json
{
  "profile": {},
  "answers": [],
  "report": {
    "score": 75,
    "strengths": [],
    "risks": [],
    "actions": []
  }
}
```

## DELETE /api/history

清空历史面试记录。

当前数据库使用 SQLite，数据库文件默认在：

```text
data/app.db
```

## GET /api/history/stats

读取历史面试统计数据。

### 返回示例

```json
{
  "total": 3,
  "averageScore": 76,
  "bestScore": 85,
  "latestScore": 80,
  "latestRole": "AI 应用开发实习生",
  "topRisks": ["项目细节不足"],
  "topActions": ["补充 STAR 案例"]
}
```

### 设计说明

- 后端从 SQLite 读取最近 50 条记录。
- 统计训练次数、平均分、最高分和最近一次得分。
- 汇总报告里的风险点和训练建议。
- 前端用这些数据渲染复盘概览面板。

## GET /api/rag/search

调试岗位知识库检索结果。

### 请求示例

```text
GET /api/rag/search?q=AI应用开发实习生&stage=技术追问
```

### 返回说明

返回当前 query 命中的知识库条目。

这个接口主要用于开发和学习 RAG，不是正式用户功能。

## GET /api/rag/debug

聚合调试两个 RAG 的检索结果。

### 请求示例

```text
GET /api/rag/debug?name=张同学&role=AI应用开发实习生&stage=技术追问
```

### 返回内容

- `roleKnowledge`：岗位知识库 RAG 命中的内容。
- `candidateMemory`：候选人画像 RAG 命中的内容。

这个接口主要用于学习和调试。前端“RAG 检索调试”面板会调用它。

## GET /api/memory/search

调试候选人画像检索结果。

### 请求示例

```text
GET /api/memory/search?name=张同学&role=AI应用开发实习生
```

### 返回说明

返回与候选人姓名、目标岗位匹配的历史画像信息。

画像信息包括：

- 历史目标岗位。
- 历史得分。
- 历史风险点。
- 历史训练建议。
- 最近回答过的面试阶段。
