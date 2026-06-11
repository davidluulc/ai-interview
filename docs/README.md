# AI 模拟面试系统文档入口

这个目录已经整理成“主线文档 + 历史归档”的结构。

平时学习和复习时，优先看主线文档，不要从 archive 里硬翻旧文件。

## 1. 学习主线

位置：`docs/learning/`

推荐顺序：

1. `00-学习总览.md`
2. `01-项目总讲解.md`
3. `02-FastAPI后端.md`
4. `03-RAG工程化.md`
5. `04-Agent工程化.md`
6. `05-部署与中间件.md`

旧的详细学习记录在：

```text
docs/learning/archive/
```

## 2. 项目路线和进度

位置：`docs/roadmap/`

- `current-state.md`
  - 当前唯一可信的项目状态和下一阶段路线入口。
- `project-progress.md`
  - 历史阶段性执行记录，用于查证做过什么。
- `deployment-preflight-checklist.md`
  - 上线前检查清单。
- `deployment-tech-selection.md`
  - 部署技术选型。

## 3. 当前仍有参考价值的 spec

位置：`docs/specs/completed/`

- `production-rag-engineering-design.md`
- `agent-engineering-v3-design.md`
- `pre-deployment-engineering-roadmap-design.md`

说明：这些文档已经执行过一轮，目前用于复盘和查漏补缺，不再表示“下一步待执行”。

真正待执行的新 spec 应放在：

```text
docs/specs/active/
```

当前 `docs/specs/active/` 暂时为空。

历史 spec 在：

```text
docs/specs/archive/
```

## 4. 当前仍有参考价值的 plan

位置：`docs/plans/completed/`

- `production-rag-engineering.md`
- `pre-deployment-engineering-roadmap.md`

说明：这些 plan 已经执行过一轮，目前用于复盘和核对，不再表示“下一步待执行”。

真正待执行的新 plan 应放在：

```text
docs/plans/active/
```

当前 `docs/plans/active/` 暂时为空。

历史 plan 在：

```text
docs/plans/archive/
```

## 5. 参考资料

位置：`docs/references/`

这里放 API、旧 MVP spec、RAG 设计、面试笔记、学习目标和一些外部讨论记录。

## 6. 你现在应该怎么看

如果你是为了找实习和准备面试：

```text
先看 learning/01-项目总讲解.md
再看 learning/03-RAG工程化.md
再看 learning/04-Agent工程化.md
最后看 learning/02-FastAPI后端.md 和 learning/05-部署与中间件.md
```

如果你是为了继续开发：

```text
先看 roadmap/current-state.md
再用 roadmap/project-progress.md 查证历史执行记录
再确认 specs/active/ 是否存在新的待执行 spec
最后确认 plans/active/ 是否存在新的待执行 plan
```

如果 `active/` 为空，说明需要先讨论并写下一阶段 spec，不要直接拿 `completed/` 里的旧文档重复执行。

注意：`docs/references/archive/ai-interview-project-learning-handbook.md` 是历史学习手册，不再作为最新开发路线依据。
