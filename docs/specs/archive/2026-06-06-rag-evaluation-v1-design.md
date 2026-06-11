# RAG 质量评估 V1 设计说明

## 背景

当前项目已经完成一条较完整的 RAG 检索链路：

```text
文档入库
-> chunk 切分
-> BM25
-> embedding 向量检索
-> hybrid 混合召回
-> qwen3-rerank 重排
-> RAG 日志可观测
```

但是只有这些功能还不够。因为系统能检索，不代表检索质量一定好；系统接入了 Hybrid 和 Rerank，也不代表它一定比 BM25 更准。

RAG 质量评估 V1 的目标是：构建一组固定评估样例，用同一批 query 对比不同检索模式的表现，输出可量化指标。这样后续优化 RAG 时就不是凭感觉判断，而是有数据依据。

## 核心概念

### 评估样例

一条评估样例描述一个“理想检索场景”：

```json
{
  "id": "rag_log_fields",
  "query": "RAG 命中日志应该记录哪些字段？",
  "knowledgeBase": "role_knowledge",
  "expectedTitle": "RAG 日志工程化",
  "expectedKeywords": ["query_text", "retriever_name", "hit_count", "quality"]
}
```

含义：

- `query`：用户真实可能提出的问题。
- `knowledgeBase`：要检索的知识库。
- `expectedTitle`：期望命中的资料标题。
- `expectedKeywords`：期望召回内容里应该覆盖的关键词。

### Hit@K

Hit@K 表示前 K 条结果中是否命中期望资料。

例如 `Hit@3`：

```text
Top 3 里有 expectedTitle -> 1
Top 3 里没有 expectedTitle -> 0
```

它回答的问题是：

> 正确资料有没有被找回来？

### MRR

MRR 表示正确资料排得靠不靠前。

单条样例的 reciprocal rank：

```text
第 1 名命中 -> 1
第 2 名命中 -> 1/2 = 0.5
第 3 名命中 -> 1/3 = 0.333
未命中 -> 0
```

多条样例取平均，就是 MRR。

它回答的问题是：

> 正确资料是不是排在靠前位置？

### 关键词覆盖率

关键词覆盖率表示召回内容是否覆盖期望知识点。

例如期望关键词：

```text
query_text, retriever_name, hit_count, quality
```

召回内容覆盖 3 个，则：

```text
keywordCoverage = 3 / 4 = 0.75
```

它回答的问题是：

> 找回来的内容是否包含关键知识点？

## 目标

RAG 质量评估 V1 实现以下能力：

- 新增一个小型评估集 JSON 文件。
- 新增独立评估模块 `backend_python/rag_evaluation.py`。
- 支持计算单条样例的：
  - Hit@K
  - reciprocal rank
  - keyword coverage
- 支持按检索模式汇总：
  - 样例数量
  - Hit@K 平均值
  - MRR
  - 平均关键词覆盖率
- 支持对比以下检索模式：
  - `bm25`
  - `vector`
  - `hybrid`
  - `hybrid_rerank`
- 新增命令行脚本 `scripts/run_rag_evaluation.py`。
- 输出 JSON 格式结果，方便后续保存、对比或展示。

## 非目标

本阶段不实现以下内容：

- 不做前端页面。
- 不新增数据库表。
- 不使用大模型当裁判。
- 不自动生成评估样例。
- 不做人工标注后台。
- 不做 CI 自动门禁。
- 不强制要求所有样例都调用真实 embedding/rerank API。

## 数据文件设计

新增文件：

```text
data/rag_evaluation_cases.json
```

结构：

```json
[
  {
    "id": "rag_log_fields",
    "query": "RAG 命中日志应该记录哪些字段？",
    "knowledgeBase": "role_knowledge",
    "expectedTitle": "RAG 日志工程化",
    "expectedKeywords": ["query_text", "retriever_name", "hit_count", "quality"]
  }
]
```

V1 先准备 5 到 10 条样例，覆盖：

- RAG 日志字段。
- FastAPI 后端模块化。
- Hybrid Search。
- Rerank 重排。
- 简历深挖或面试追问策略。

## 评估模块设计

新增文件：

```text
backend_python/rag_evaluation.py
```

核心函数：

```python
def normalize_text(value: object) -> str:
    ...


def is_expected_hit(hit: dict, expected_title: str, expected_keywords: list[str]) -> bool:
    ...


def calculate_hit_at_k(hits: list[dict], expected_title: str, expected_keywords: list[str], k: int) -> int:
    ...


def calculate_reciprocal_rank(hits: list[dict], expected_title: str, expected_keywords: list[str]) -> float:
    ...


def calculate_keyword_coverage(hits: list[dict], expected_keywords: list[str], k: int) -> float:
    ...


def evaluate_case(case: dict, hits: list[dict], k: int) -> dict:
    ...


def summarize_mode_results(results: list[dict]) -> dict:
    ...
```

### 命中判定

V1 采用标题和关键词双规则：

- 如果 hit 的 `title` 包含 `expectedTitle`，算命中。
- 或者 hit 的 `content` 覆盖至少一个 `expectedKeywords`，也算弱命中。

这样做是为了避免标题稍有差异时完全判错。

### 关键词覆盖范围

关键词覆盖率只看 Top K 的拼接内容：

```text
Top K title + content + metadata
```

如果 `expectedKeywords` 为空，则 coverage 记为 0，避免伪造高分。

## 命令行脚本设计

新增文件：

```text
scripts/run_rag_evaluation.py
```

运行方式：

```powershell
python scripts/run_rag_evaluation.py
```

默认行为：

- 读取 `data/rag_evaluation_cases.json`。
- 使用一个评估专用用户或默认用户。
- 对每条 case 分别执行：
  - `retrieve_chunks(mode="bm25")`
  - `retrieve_chunks(mode="vector")`
  - `retrieve_chunks(mode="hybrid")`
  - `retrieve_chunks(mode="hybrid_rerank")`
- 计算每种模式的指标。
- 输出 JSON。

输出示例：

```json
{
  "k": 3,
  "modes": {
    "bm25": {
      "caseCount": 5,
      "hitAtK": 0.6,
      "mrr": 0.43,
      "keywordCoverage": 0.55
    },
    "hybrid_rerank": {
      "caseCount": 5,
      "hitAtK": 0.8,
      "mrr": 0.7,
      "keywordCoverage": 0.76
    }
  }
}
```

## 关于真实模型调用

`vector`、`hybrid`、`hybrid_rerank` 可能触发 embedding 或 rerank API。

V1 采取保守策略：

- 单元测试中 mock 模型调用，不消耗 API 额度。
- 命令行脚本真实运行时再使用 `.env` 中的百炼 API Key。
- 如果某个模式失败，记录该模式错误，不影响其它模式继续评估。

## 验收标准

- 评估样例文件存在且结构明确。
- 单条 case 能计算 Hit@K、reciprocal rank、keyword coverage。
- 多条 case 能按模式汇总平均指标。
- 命令行脚本能输出 JSON 结果。
- 模型调用失败不会导致整个评估脚本崩溃。
- 不影响现有 RAG 检索、Rerank、日志功能。
- 全量后端测试通过。

## 面试表达建议

可以这样讲：

> 我没有只凭主观体验判断 RAG 是否变准，而是构建了一个小型 RAG 评估集。每条样例包含 query、目标知识库、期望命中的标题和关键词。系统会用同一批样例分别测试 BM25、Vector、Hybrid 和 Hybrid + Rerank，并计算 Hit@K、MRR 和关键词覆盖率。这样可以量化不同检索策略的效果，判断新增 Hybrid 或 Rerank 是否真的改善了召回质量。

