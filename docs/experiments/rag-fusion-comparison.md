# RAG 混合检索融合策略对比实验（weighted vs rrf）

- 阶段：Agent v3 升级 S3（RRF fusion experiment）
- 运行日期：2026-09-09（真实向量侧 04:26:58，mock 对照组 04:26:59）
- 脚本：`scripts/rag_fusion_experiment.py`（复现命令见文末）
- 环境：本地 SQLite（`VECTOR_SEARCH_BACKEND=sqlite`），`HYBRID_FUSION_MODE` 默认=weighted；语料为 user=1 名下 evaluation_seed chunks 38 条（ready embedding=38）

## 背景

混合检索此前只有 weighted 一种融合：bm25 / vector 两路分数 min-max 归一化后按 0.6 / 0.4 加权（`normalize_hybrid_weights` 默认值）。这组权重从最初沿用至今，从未做过对照验证。S3 引入 rrf 融合（按各路名次倒数 1/(60+rank) 融合，天然不依赖两路分数分布，bm25/vector 权重仅 weighted 模式生效），需要回答：默认融合策略应该用哪个。

## 方法

- 四组模式：bm25 / vector / hybrid-weighted / hybrid-rrf；k=3、limit=3，与现有评测口径一致。
- 指标：hit@3、MRR、keywordCoverage、总耗时（本地 SQLite 单进程 wall time）。
- 用例：`data/rag_evaluation_cases.json` 共 38 例。
- 向量侧两种跑法：
  1. 真实 `embed_text`——本地 `.env` 未配置 embedding key，向量一路为空召回（检测详情：`500: Missing embedding API key in .env.`）；
  2. `--mock-vector` 静态向量对照组——复用 `run_rag_evaluation.py` 的 case→固定 3 维向量映射（24/38 例显式映射，其余 14 例默认 [1,0,0]），使四组在本地完整可评。

## 结果一：真实向量侧（无 key，向量路为空）

| 模式 | caseCount | hit@3 | MRR | keywordCoverage | 耗时(ms) |
| --- | --- | --- | --- | --- | --- |
| bm25 | 38 | 0.8947 | 0.8772 | 0.8355 | 124.2 |
| vector | 38 | 0.0000 | 0.0000 | 0.0000 | 3.4 |
| hybrid-weighted | 38 | 0.8947 | 0.8772 | 0.8355 | 148.8 |
| hybrid-rrf | 38 | 0.8947 | 0.8772 | 0.8355 | 122.7 |

bm25 / hybrid-weighted / hybrid-rrf 三组数字完全相同不是巧合：向量侧为空时，weighted 是 bm25 分数的 min-max 单调归一化、rrf 是名次的单调函数，两种融合在数学上都退化为与 bm25 相同的排序——脚本实测 38/38 例 top3 顺序完全一致。**该表不构成融合策略对比证据**，价值仅是验证两条融合代码路径在空向量侧下行为一致、不崩溃。每 case 平均耗时(ms)：bm25=3.27，vector=0.09，hybrid-weighted=3.92，hybrid-rrf=3.23。

## 结果二：mock 静态向量对照组（--mock-vector）

| 模式 | caseCount | hit@3 | MRR | keywordCoverage | 耗时(ms) |
| --- | --- | --- | --- | --- | --- |
| bm25 | 38 | 0.8947 | 0.8772 | 0.8355 | 119.5 |
| vector | 38 | 0.6579 | 0.4912 | 0.5921 | 115.7 |
| hybrid-weighted | 38 | 0.9474 | 0.8991 | 0.9079 | 216.1 |
| hybrid-rrf | 38 | 0.9737 | 0.8860 | 0.9211 | 221.3 |

weighted 与 rrf 的 top3 顺序完全一致的 case 数：14/38——即 38 例中 24 例两种融合排序不同。每 case 平均耗时(ms)：bm25=3.14，vector=3.04，hybrid-weighted=5.69，hybrid-rrf=5.82。

## 结论

- mock 组 rrf 胜 hit@3：0.9737 vs 0.9474（keywordCoverage 0.9211 vs 0.9079 同向）。
- mock 组 rrf MRR 负于 weighted：0.8860 vs 0.8991。粗解读：rrf 只看名次、对两路分数分布不敏感，能保进更多“任一路排前”的候选（hit 面更宽）；weighted 按归一化分数加权，bm25 单路强信号（第一名归一化 1.0 × 0.6）更易占据首位（首位精度更高）。
- 耗时：两种融合同量级（rrf 无归一化计算；本次真实跑 122.7 vs 148.8，mock 跑 221.3 vs 216.1，方向不一致，仅相对参考）。

## 决策：默认保持 weighted

唯一可比较的证据来自 mock 方法论（静态 3 维向量、分布人工构造、14/38 例默认映射 [1,0,0] 系统性偏向部分内容），且结论本身分裂（hit@3 rrf 胜、MRR weighted 胜），不足以推翻现状默认。真实向量证据本地不可得（无 embedding API key），与 S2 pgvector 切换同窗口补跑。

**切换条件（预设）**：部署窗口 pgvector 切换后用真实向量复跑本实验，若 rrf hit@3 仍 ≥ weighted，则将 `HYBRID_FUSION_MODE` 默认切为 rrf（`backend_python/config.py` 默认值 + `.env.example` 注释 + 测试默认值断言，一行级改动）。

复跑陷阱（实验脚本实测）：seed 语料 embedding_model=`evaluation-static` ≠ 默认 `EMBEDDING_MODEL`=`text-embedding-v4`，向量检索按模型名过滤——复跑前要么设 `EMBEDDING_MODEL=evaluation-static`，要么用真实 embedding 重新灌 seed，否则向量侧同样被模型过滤清空、跑出“结果一”。另外 seed 判定必须以 user=1 可见性视角统计（本地库的全局 chunks 属于其他用户）。

## 局限

- mock 向量分布人工构造（case→固定 3 维向量），与真实 2048 维语义向量不可比；该跑法仅用于本地完整对比两路都有召回时两种融合的排序差异。
- 种子语料为评测构造，非生产流量分布；case 数 38。
- 无真实向量组（本地无 key）；真实组待部署窗口 pgvector 环境补跑。
- keywordCoverage 与耗时如实附上：耗时为本地 SQLite 单进程 wall time（含 mock 进程内向量计算），仅做相对比较。

## 复现

```bash
# 真实向量侧（本地无 embedding key 时 vector 组空召回，见“结果一”）
python scripts/rag_fusion_experiment.py

# mock 静态向量对照组（四组完整可评，见“结果二”）
python scripts/rag_fusion_experiment.py --mock-vector

# --append：把本次输出累积追加到 scratch 输出文件（默认覆盖）
python scripts/rag_fusion_experiment.py --mock-vector --append
```

脚本会自动 seed user=1 的 evaluation 语料（幂等）并双写 stdout 与本地 scratch 输出文件；`--mock-vector` 在进程内 monkeypatch `embed_text` 与 `current_embedding_model`（后者必须返回 `evaluation-static`，向量检索按模型名过滤），不改任何生产文件。
