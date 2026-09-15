# AI 面试系统前端重设计 · 新粗野主义 × ISO 语义色 设计规格

- 日期：2026-09-16
- 状态：待用户评审
- 范围：frontend/ 全部 12 个页面深度重设计（纯前端，后端/接口/数据零改动）
- 交付终点：合并 main → 推送 GitHub → VPS 生产发布

## 0. 背景与目标

现有前端为"AI 默认脸"（Apple 克隆配色 + 英文 eyebrow + 白卡片堆叠），与产品的工程级内核
（Agent 决策、RAG 证据链、策略护栏、逐题评分）完全脱节。本次重设计目标：

1. 视觉去模板化：一眼不像 LLM 生成的默认 UI
2. 颜色即语言：配色与系统语义（合格/护栏/不合格/指令）一一对应
3. 排版服务核心交互：面试的"问题→回答"是产品主角
4. 行为与测试零破坏：所有 `data-testid`、stores、API 调用保持不变

## 1. 已定决策记录（探索全程结论）

| 决策点 | 结论 | 探索过程 |
|---|---|---|
| 美学方向 | 新粗野主义（J） | 12 个方向小样对比（驾驶舱/纸感/印刷/终端/瑞士/蓝图/行情/粗野/论文/DOS 等） |
| 力度 | 激进档 | 克制版 vs 激进版整页对比，用户选激进 |
| 配色 | ISO 3864 安全色语义系统 | 18 个配色方案 + "颜色与系统结合"方法论讨论后确立 |
| 版式 | V2 聚焦模式（问题为主角） | 三版式变体（顶部指挥条/聚焦/骨架精修）对比后选定 |
| 字体 | 六档字阶 + 等宽数据字 | frontend-design skill 规范 |
| 范围 | 全部 12 页深度重设计 | 用户明确选择 |

密度分级规则（T1/T2/T3，见 §5）解决"激进力度 × 数据密集页"的矛盾。

## 2. 设计令牌（替换 frontend/src/styles/tokens.css）

全部落成 CSS custom properties，一处定义全站引用，禁止页面内散写色值。

```css
:root {
  /* 中性层：永不表义 */
  --paper: #fdfcf7;        /* 页面底 */
  --panel: #ffffff;        /* 面板 */
  --panel-warm: #fff3bf;   /* 用户回答区 */
  --ink: #141414;          /* 墨字/边框 */
  --ink-soft: #6b6558;     /* 次级文字 */
  --line-hair: #e5e1d5;    /* 内部发丝线 */

  /* 动作层：唯一交互色（激活导航/主按钮/灰度链路标记） */
  --action: #005eb8;
  --action-ink: #ffffff;

  /* 语义层：专用，绝不做装饰 */
  --ok: #009639;       /* 合格/通过/安全 */
  --warn: #ffd100;     /* 护栏触发/待改进/降级 */
  --danger: #c8102e;   /* 不合格/失败/错误 */
  --info: #005eb8;     /* 指令/规则/灰度标记（与动作同源） */

  /* 数据梯度：分数=蓝 5 档，热度=红 3 档 */
  --score-5: #005eb8; --score-4: #4d84c8; --score-3: #9dbfe2;
  --score-2: #cfe0f0; --score-1: #e8f0f8;
  --heat-3: #c8102e; --heat-2: #ff8a80; --heat-1: #ffd9d6;

  /* 粗野令牌 */
  --line: 2px solid var(--ink);
  --shadow-2: 2px 2px 0 var(--ink);
  --shadow-3: 3px 3px 0 var(--ink);
  --shadow-4: 4px 4px 0 var(--ink);
  --shadow-5: 5px 5px 0 var(--ink);
  --hazard: repeating-linear-gradient(45deg, var(--ink) 0 6px, var(--warn) 6px 12px);

  /* 字阶（px / weight / 用途） */
  --font-ui: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  --font-mono: ui-monospace, "Cascadia Code", Consolas, "SF Mono", monospace;
  /* 28/900 页题 · 20/900 区块 · 15/800 强内容 · 12.5/400 正文 · 10.5/900 标签 · 9/mono 数据 */
  --text-page: 28px; --text-section: 20px; --text-strong: 15px;
  --text-body: 12.5px; --text-label: 10.5px; --text-data: 9px;

  /* 间距：8pt 网格 */
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px; --s6: 24px;

  /* 圆角锁定 0（粗野主义直角） */
  --radius: 0;
}
```

规则：动作蓝与语义 info 同源（`#005eb8` 既是 ISO 指令蓝又是交互蓝）；语义四色只出现在
对应语义位；黑边与硬投影永远只管结构，不参与表义。

## 3. 共享组件库（frontend/src/components/brut/）

新建约 16 个组件，全站复用：

| 组件 | 职责 |
|---|---|
| BrutButton | 主/次/危险按钮，8 状态（默认/hover/focus/active/禁用/加载/错误/成功） |
| BrutChip | 状态芯片（语义色底 + 墨边） |
| BrutStamp | 判定贴纸（旋转 2°，盖章感，合格绿/待改黄/不合格红） |
| BrutPanel | 黑头白身面板（区块容器） |
| HazardBanner | 护栏横幅（警戒斜纹条 + 黄底），guardrail 专用 |
| ScoreBlock | 海报级评分块（蓝色大数字 + 说明） |
| ChunkChip | RAG 命中芯片（蓝色梯度按分数深浅） |
| HeatChip | 弱项热度芯片（红色梯度） |
| ProgressBlocks | 分块进度条（绿=过 红=败 斜纹=当前） |
| ModeSeg | 模式分段切换 |
| RoundLedger | 轮次台账（面试页专用结构） |
| QuestionStage | 问题舞台（展示级排版 + 蓝标签帽） |
| AnswerBox | 回答区（暖黄面板） |
| BrutField | 表单组（label 在上，等宽字体数据输入） |
| BrutEmpty | 空状态（构图化，指明如何填充） |
| BrutSkeleton | 骨架屏（匹配最终布局形状，不用转圈） |

## 4. 页面结构设计（每页独立宏观结构，不做换色模板）

| 页面 | 结构概念 | 密度档 |
|---|---|---|
| 登录/注册 | 海报式聚焦卡：黑头"进入工作台"，语义错误内联 | T1 |
| **面试台** | **V2 聚焦模式**：左轮次台账（Q1✓ Q2✕ Q3 回答中）+ 中问题舞台（20px 展示排版 + 回答区紧贴）+ 右证据链（护栏横幅/评分块/RAG 命中/决策摘要） | T1 |
| 报告页 | 评分英雄块 → 优势(绿)/风险(黄)面板 → 逐题复盘卡（判定贴纸 + 缺失点热度芯片）→ 训练处方笺 | T1 头部 / T2 正文 |
| 训练页 | 弱项热度图 → 任务卡（语义状态）→ 练习面板 | T1 头部 / T2 列表 |
| 复盘列表 | 会话台账行：大数字评分 + 热度芯片 + 判定章 | T2 |
| 档案页 | 投递档案身份卡（公司/岗位/难度），激活卡蓝底 | T2 |
| 知识库 | 文档台账行（嵌入状态芯片：就绪/处理中/失败）+ 分块抽屉 | T2 |
| 设置 | 表单页，分节黑头 | T3 |
| 后台 | 工具级：黑头分节表格，投影仅交互元素 | T3 |

面试台组件迁移：InterviewChatPanel 拆为 QuestionStage + AnswerBox；消息数据模型不变，
相关测试（interview-page.test.ts / InterviewChatPanel.test.ts）随组件结构迁移，
`data-testid` 全部保留。

## 5. 密度分级规则

- **T1 激进**（签名交互面）：全块面装框 + 硬投影 + 贴纸 + 警戒斜纹
- **T2 标准**（数据密集面）：面板装框，投影只给交互元素，内部行用发丝线
- **T3 工具**（后台/设置）：令牌换肤 + 黑头分节，投影仅限按钮/激活项

规则本身是可讲的设计决策：激进但不成噪音，力度随信息密度自动收敛。

## 6. 交互与动效规范（emil-design-eng）

- 按压反馈：`transform: scale(0.97)`，120ms
- 全部动效 `ease-out`（自定义曲线 `cubic-bezier(0.23,1,0.32,1)`），≤200ms
- Enter 提交等高频操作：零动画
- 只动 `transform/opacity`，不动布局属性
- `prefers-reduced-motion: reduce`：位移动效退化为 ≤150ms 淡入淡出
- `:focus-visible`：2px 墨色环，即时出现不参与动画
- 悬停抬起仅限交互元素，且包在 `@media (hover:hover) and (pointer:fine)` 内

## 7. 工程红线

1. **零行为变更**：stores / api / router 逻辑不动；全部 `data-testid` 保留
2. **零新运行时依赖**：纯 CSS 设计系统 + 现有 Vue3 栈
3. **门禁**：每个实施任务完成时 `npm run build`（含 vue-tsc）与 `npx vitest run` 全绿
4. 现有 tokens.css 被替换；base.css 保留 reset 部分
5. 所有页面 `<style scoped>` 中的散写色值收敛到令牌引用

## 8. 响应式

断点 1040px / 760px。窄屏降级：面试台 V2 降为单列（轮次台账变横向芯片行，证据链折叠
到回答区下方）；所有多栏布局显式声明窄屏回退。

## 9. 实施顺序

令牌 → 共享组件库 → 登录/注册（快速验证）→ 面试台 V2 → 报告页 → 训练页 →
复盘列表 → 档案页 → 知识库 → 设置 → 后台 → README 更新（截图 + 设计系统说明）。

## 10. 交付与发布（用户明确要求）

1. **合并 main**：全部页面完成、全部门禁绿后合并
2. **推送 GitHub**：origin main（如遇网络问题走 gh-proxy 备选）
3. **VPS 生产发布**（124.221.230.218，ssh 别名 `vps`，密钥 `~/.ssh/tencent_lighthouse_ed25519`）：
   - 前端为静态托管：`frontend/dist` bind-mount 进 nginx 容器（`deploy/nginx/ai-interview.conf`）
   - 发布流程：服务器拉取（或直推，仓库已设 `receive.denyCurrentBranch=updateInstead`）→
     构建 `frontend/dist`（实施时确认服务器 node 环境，否则本地构建后 rsync dist）→
     无需重建后端容器（纯前端变更）→ 页面抽查
   - 沿用 9 月 9 日部署窗口 runbook 纪律：变更前确认备份存在；健康门禁 `/api/health` 200；
     公网抽查页面；nginx 若有配置变更需重启（上游 DNS 缓存规则）
   - 回滚：dist 目录备份后覆盖即回滚（静态托管优势）

## 11. 验收门禁

- [ ] 12 页全部换装，无旧样式残留（grep 检查 `--color-accent` 等旧令牌零引用）
- [ ] `npm run build` + `npx vitest run` 全绿（测试数不减少，允许随组件迁移改名）
- [ ] 语义色审计：绿/黄/红只出现在语义位（抽查报告页/面试台）
- [ ] 对比度抽查：语义色上文字 WCAG AA（黄底用墨字）
- [ ] 键盘走查：焦点环可见，Enter 提交可用
- [ ] 生产发布后公网抽查：登录 → 面试台 → 生成一题 → 报告页
- [ ] README 更新：新截图 + 设计系统一节（令牌表 + 密度分级）

## 12. 风险与缓解

| 风险 | 缓解 |
|---|---|
| AdminPage 2141 行改造量大 | T3 降档策略：令牌换肤为主，结构不动 |
| V2 结构迁移碰坏面试流测试 | 测试随组件先行迁移；`data-testid` 保留保底 |
| 激进风格在密集页变噪音 | 密度分级规则硬约束 |
| 服务器无 node 构建环境 | 实施时探测；本地构建 + rsync dist 兜底 |
| 用户观感不合 | 签名页（面试台）先出真页验收，再铺开其余页面 |
