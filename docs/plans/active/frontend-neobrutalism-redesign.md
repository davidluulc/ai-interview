# 前端新粗野主义重设计 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按已批准规格 `docs/specs/active/frontend-neobrutalism-redesign-design.md` 将 frontend/ 全部 12 页换装为新粗野主义 × ISO 语义色设计系统，零行为变更，终点为 GitHub 推送 + VPS 生产发布。

**Architecture:** 令牌层（CSS custom properties）→ Brut* 共享组件层 → 页面层逐页迁移。旧令牌保留为别名直到全部页面迁移完成后统一清理。面试台按 V2 聚焦模式重构组件结构。

**Tech Stack:** Vue 3.5 + `<script setup lang="ts">` + scoped CSS（零新依赖）、Vitest + @vue/test-utils（jsdom）。

## Global Constraints（每个任务隐含遵守）

- 零行为变更：stores / api / router 逻辑不动；模板中所有 `data-testid` 属性原样保留
- 零新运行时依赖：只允许 CSS 与现有依赖
- 每任务门禁：`cd frontend && npm run build` 全绿（含 vue-tsc）且 `npx vitest run` 不低于基线通过数
- 圆角一律 0；颜色只引用令牌（`var(--...)`），scoped 样式内不写裸 hex
- 语义色只出现在语义位：`--ok` 合格、`--warn` 护栏/待改进、`--danger` 不合格、`--action/--info` 交互与指令
- 等宽字体 `var(--font-mono)` 只用于数字/ID/trace；分数类文本加 `font-variant-numeric: tabular-nums`
- 语义色上的文字对比：黄底必须墨字（`var(--ink)`），绿/红/蓝底用白字
- 提交信息格式沿用仓库惯例（`feat:`/`fix:`/`refactor:`/`docs:`/`chore:`）

## 令牌契约（Task 1 定义，后续任务消费）

```css
/* frontend/src/styles/tokens.css 追加块（保留旧块直至 Task 16） */
:root {
  --paper: #fdfcf7; --panel: #ffffff; --panel-warm: #fff3bf;
  --ink: #141414; --ink-soft: #6b6558; --line-hair: #e5e1d5;
  --action: #005eb8; --action-ink: #ffffff;
  --ok: #009639; --warn: #ffd100; --danger: #c8102e; --info: #005eb8;
  --score-5: #005eb8; --score-4: #4d84c8; --score-3: #9dbfe2; --score-2: #cfe0f0; --score-1: #e8f0f8;
  --heat-3: #c8102e; --heat-2: #ff8a80; --heat-1: #ffd9d6;
  --line: 2px solid var(--ink);
  --shadow-2: 2px 2px 0 var(--ink); --shadow-3: 3px 3px 0 var(--ink);
  --shadow-4: 4px 4px 0 var(--ink); --shadow-5: 5px 5px 0 var(--ink);
  --hazard: repeating-linear-gradient(45deg, var(--ink) 0 6px, var(--warn) 6px 12px);
  --font-ui: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  --font-mono: ui-monospace, "Cascadia Code", Consolas, "SF Mono", monospace;
  --text-page: 28px; --text-section: 20px; --text-strong: 15px;
  --text-body: 12.5px; --text-label: 10.5px; --text-data: 9px;
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px; --s6: 24px;
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}
```

## 组件 API 契约（Task 2-5 定义，页面任务消费；目录 `frontend/src/components/brut/`）

- `BrutButton.vue`：props `variant: "primary" | "ghost" | "danger"`、`disabled?: boolean`、`loading?: boolean`；默认插槽为文案；透传 attrs（含 data-testid）；8 状态样式
- `BrutChip.vue`：props `tone: "ok" | "warn" | "danger" | "info" | "neutral"`、`label: string`
- `BrutStamp.vue`：props `verdict: "pass" | "warn" | "fail"`、`text: string`；旋转 2°
- `BrutPanel.vue`：props `title: string`；默认插槽为面板体
- `HazardBanner.vue`：props `title: string`、`detail: string`；左侧警戒斜纹条
- `ScoreBlock.vue`：props `score: number`、`caption: string`
- `ChunkChip.vue`：props `label: string`、`score: number`（≥0.8→score-5，≥0.7→score-4，≥0.6→score-3，≥0.5→score-2，否则 score-1）
- `HeatChip.vue`：props `label: string`、`count: number`（≥3→heat-3，=2→heat-2，否则 heat-1）
- `ProgressBlocks.vue`：props `total: number`、`current: number`、`prior: Array<"pass" | "fail">`（长度 = current-1）
- `ModeSeg.vue`：props `options: Array<{ value: string; label: string }>`、`modelValue: string`；emit `update:modelValue`
- `RoundLedger.vue`：props `rounds: Array<{ index: number; label: string; status: "pass" | "fail" | "current" | "todo" }>`
- `QuestionStage.vue`：props `tag: string`、`text: string`、`meta: string[]`
- `AnswerBox.vue`：props `modelValue: string`、`placeholder: string`、`hint: string`；emit `update:modelValue`、`submit`
- `BrutField.vue`：props `label: string`、`modelValue: string`、`type?: string`、`placeholder?: string`；emit `update:modelValue`
- `BrutEmpty.vue`：props `title: string`、`actionLabel: string`；emit `action`
- `BrutSkeleton.vue`：props `variant: "panel" | "rows"`、`rows?: number`

---

### Task 0: 基线记录

**Files:** 无新建；产出 `docs/plans/active/frontend-redesign-baseline.md`（记录数字）

- [ ] **Step 1:** `cd frontend && npx vitest run 2>&1 | tail -5`，记录通过/总数 X/Y
- [ ] **Step 2:** `npm run build 2>&1 | tail -3`，确认构建绿
- [ ] **Step 3:** 把两个数字写入 baseline 文件并提交 `chore: record frontend redesign baseline`

### Task 1: 设计令牌落地

**Files:**
- Modify: `frontend/src/styles/tokens.css`（追加新块，保留旧块）
- Test: `frontend/src/styles/tokens.test.ts`（新建）

- [ ] **Step 1: 写失败测试**（读文件断言关键令牌存在）

```ts
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");

describe("brut tokens", () => {
  it.each(["--paper", "--ink", "--action", "--ok", "--warn", "--danger", "--score-5", "--heat-3", "--shadow-3", "--hazard", "--font-mono", "--text-page", "--s4", "--ease-out"])("defines %s", (token) => {
    expect(css).toContain(`${token}:`);
  });
});
```

- [ ] **Step 2:** 运行 `npx vitest run src/styles/tokens.test.ts`，预期 FAIL
- [ ] **Step 3:** 按上方「令牌契约」完整追加到 tokens.css
- [ ] **Step 4:** 测试转绿；`npm run build` 绿；全量 vitest 不低于基线
- [ ] **Step 5:** 提交 `feat: add neo-brutalism design tokens`

### Task 2: 基础组件 BrutButton / BrutChip / BrutStamp

**Files:**
- Create: `frontend/src/components/brut/BrutButton.vue`、`BrutChip.vue`、`BrutStamp.vue`
- Test: `frontend/src/components/brut/brut-basics.test.ts`

**实现要点**（三件套共同规范：`border: var(--line)`、直角、字体 `var(--font-ui)`）：
- BrutButton：primary=墨底黄字 + `--shadow-4`；ghost=白底墨字 + `--shadow-3`；danger=`--danger` 底白字；`:active { transform: scale(0.97) }` 120ms `var(--ease-out)`；`:focus-visible` 2px 墨色外环即时出现；disabled 降透明度 0.5 且去投影；loading 显示"处理中…"并禁点；`@media (hover:hover) and (pointer:fine)` 内 hover 抬升 `translateY(-1px)`
- BrutChip：tone→底色映射 ok/warn/danger/info/neutral（warn 墨字，其余白字，neutral 白底墨字）+ 2px 墨边
- BrutStamp：verdict→pass绿/warn黄/fail红，`transform: rotate(2deg)`，`--shadow-2`，字重 900

- [ ] **Step 1:** 写失败测试：挂载三组件断言 class/tone/verdict 映射、BrutButton disabled/loading 属性、attrs 透传（`data-testid="x"` 出现在根元素）
- [ ] **Step 2:** 运行确认 FAIL → **Step 3:** 实现三组件 → **Step 4:** 全量门禁 → **Step 5:** 提交 `feat: add brut base components`

### Task 3: 面板与警示组件 BrutPanel / HazardBanner / ScoreBlock

**Files:**
- Create: `frontend/src/components/brut/BrutPanel.vue`、`HazardBanner.vue`、`ScoreBlock.vue`
- Test: `frontend/src/components/brut/brut-panels.test.ts`

**实现要点：**
- BrutPanel：黑头（墨底纸色字，`--text-label` 900 字重）+ 白身 + `--shadow-4`，标题槽位为 prop `title`
- HazardBanner：黄底 + 左 14px `--hazard` 斜纹条（右墨边分隔）+ 800 字重标题与明细，`--shadow-4`
- ScoreBlock：`--action` 蓝底、36px 900 等宽大数字（tabular-nums）+ 左侧说明列，`--shadow-4`

- [ ] **Step 1-5:** 测试（断言黑头存在、斜纹条 class、数字渲染为 "87"）→ FAIL → 实现 → 门禁 → 提交 `feat: add brut panel components`

### Task 4: 数据组件 ChunkChip / HeatChip / ProgressBlocks / ModeSeg

**Files:**
- Create: `frontend/src/components/brut/ChunkChip.vue`、`HeatChip.vue`、`ProgressBlocks.vue`、`ModeSeg.vue`
- Test: `frontend/src/components/brut/brut-data.test.ts`

**实现要点：**
- ChunkChip：按 score 分档到 score-5..1 档位 class，等宽字重 900
- HeatChip：按 count 分档 heat-3..1；label 显示 `系统设计 ×3` 格式（count 拼接）
- ProgressBlocks：total 块，前 prior.length 块按 prior 上绿/红，第 current 块 `--hazard` 斜纹，其余白底
- ModeSeg：分段切换，激活段 `--action` 蓝底白字，emit update:modelValue，键盘可达（button 元素）

- [ ] **Step 1-5:** 测试（分档断言：ChunkChip score 0.87→tier-5、HeatChip count 3→tier-3、ProgressBlocks 5 块 3 色、ModeSeg 点击触发 emit）→ FAIL → 实现 → 门禁 → 提交 `feat: add brut data components`

### Task 5: 表单与状态组件 BrutField / BrutEmpty / BrutSkeleton

**Files:**
- Create: `frontend/src/components/brut/BrutField.vue`、`BrutEmpty.vue`、`BrutSkeleton.vue`
- Test: `frontend/src/components/brut/brut-form.test.ts`

**实现要点：**
- BrutField：label 在输入框上方（`--text-label` 900），输入框 2px 墨边白底，focus 墨色外环
- BrutEmpty：构图化空状态：黑头小面板 + 标题 + BrutButton 行动按钮，emit `action`
- BrutSkeleton：panel 变体（黑头 + 灰块）/rows 变体（N 条发丝线灰块），静态无动画

- [ ] **Step 1-5:** 测试（v-model 双向、emit action、rows 数量）→ FAIL → 实现 → 门禁 → 提交 `feat: add brut form components`

### Task 6: 全局骨架 AppLayout + 认证页（T1 海报卡）

**Files:**
- Modify: `frontend/src/layouts/AppLayout.vue`、`AuthLayout.vue`、`frontend/src/pages/auth/LoginPage.vue`、`RegisterPage.vue`
- Test: 既有 `src/layouts/app-layout.test.ts`、`src/pages/auth/auth-pages.test.ts` 必须保持绿

**结构规格：**
- AppLayout：纸底；侧栏白底墨右边；brand 为 `--action` 蓝底白字块 + `--shadow-4`；导航项 2px 墨边白底 + `--shadow-3`，激活项黄底（`--warn`）墨字；退出为虚线边项。760px 断点变横向滚动条保持现行为
- AuthLayout：居中海报卡（2px 墨边 + `--shadow-5`），黑头带"AI 面试 / 进入工作台"
- LoginPage/RegisterPage：改用 BrutField + BrutButton；错误信息 `--danger` 墨边芯片；保留全部 data-testid 与既有文案

- [ ] **Step 1:** 跑既有两个测试文件记录绿 → **Step 2:** 重写样式与模板（script 逻辑不动）→ **Step 3:** 既有测试全绿 + 全量门禁 → **Step 4:** 提交 `feat: redesign app layout and auth pages`

### Task 7: 面试台 V2 之组件（QuestionStage / AnswerBox / RoundLedger）

**Files:**
- Create: `frontend/src/components/brut/QuestionStage.vue`、`AnswerBox.vue`、`RoundLedger.vue`
- Test: `frontend/src/components/brut/brut-interview.test.ts`

**实现要点：**
- QuestionStage：白底 + `--shadow-6`(即 6px) 硬投影；顶部悬浮蓝标签帽（`--action` 底白字 + `--shadow-3`，`position: absolute; top: -13px`）；问题文本 `--text-section`(20px)/800 字重、行高 1.55、`max-width: 30em`；meta 芯片行
- AnswerBox：`--panel-warm` 暖黄面板 + `--shadow-5`；label 行（"你的回答" 900 字重 + 右侧 hint `--ink-soft`）；textarea 2px 墨边白底 12px/1.8；Enter 提交 emit、Shift+Enter 换行
- RoundLedger：BrutPanel 黑头"轮次台账"；行 = 序号(mono 900) + 标签 + 状态章；status 映射 pass→绿✓ / fail→红✕ / current→黄底墨字"回答中" / todo→灰
- [ ] **Step 1-5:** 测试（QuestionStage 渲染 tag/text/meta；AnswerBox v-model + Enter emit；RoundLedger 四状态 class）→ FAIL → 实现 → 门禁 → 提交 `feat: add interview v2 stage components`

### Task 8: 面试台 V2 之页面重构

**Files:**
- Modify: `frontend/src/pages/app/InterviewPage.vue`、`frontend/src/components/interview/InterviewChatPanel.vue`（拆分）、`InterviewProgressStrip.vue`、`InterviewEvidencePanel.vue`、`CurrentProfileBanner.vue`、`InterviewSessionSetup.vue`
- Test: 既有 `interview-page.test.ts`、`InterviewChatPanel.test.ts` 随组件迁移更新

**结构规格（V2 三栏 grid：`176px 1fr 268px`，1040px 断点降单列、台账变横向芯片行）：**
- 左：RoundLedger（数据由 interview store 的 answeredHistory/rounds 推导：已答轮 pass/fail 按 answerStatus，当前轮 current，未生成 todo）
- 中：顶部窄黑条（brand 黄块 + 导航链接组 + 右侧"轮次 3/5 难度 P6 链路"meta）；QuestionStage（当前问题 = messages 最后一条面试官消息）；AnswerBox（draft v-model，提交按钮 BrutButton"提交回答"）
- 右：HazardBanner（decisionSummary 有 overrideReason 时显示）+ ScoreBlock（decisionSummary 分数）+ BrutPanel"RAG 命中"（ChunkChip 行）+ BrutPanel"决策摘要"（ModeSeg 换掉 InterviewModeSwitch 的样式、保留其 data-testid）
- **data-testid 映射（硬规则）**：旧模板里全部 testid 原样迁到新结构对应元素（含 runtime-classic/shadow/langgraph-canary、start-interview、草稿输入、提交按钮等）
- script 部分逻辑不动；仅新增由 store 状态推导 rounds 的 computed

- [ ] **Step 1:** 迁移/更新既有测试断言到新组件结构 → **Step 2:** 实现 → **Step 3:** 全量门禁 → **Step 4:** 提交 `feat: redesign interview page to v2 focus mode`

### Task 9: 报告页（T1 头部 / T2 正文）

**Files:** Modify: `frontend/src/pages/app/ReportPage.vue`；Test: 既有 `report-page.test.ts` 保持绿

**结构规格：** 页首 ScoreBlock（总分 + 一行说明）→ 双面板：优势(BrutPanel + BrutChip ok 行)/风险(BrutChip warn 行) → 逐题复盘卡（BrutPanel 每题：BrutStamp 判定 + 问题文本 --text-strong + missingPoints 为 HeatChip 行 + whyAsked/referenceDirection 正文）→ 训练处方笺（BrutPanel：weakTopics HeatChip + oneMinuteTemplates 等正文）。fallbackUsed 时顶部 BrutChip warn"模型复盘降级"。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign report page`

### Task 10: 训练页（T1 头部 / T2 列表）

**Files:** Modify: `frontend/src/pages/app/TrainingPage.vue`、`frontend/src/components/training/*.vue`；Test: 既有 `training-page.test.ts` 等保持绿

**结构规格：** 头部概览（TrainingOverviewCards 换 BrutPanel + ScoreBlock 缩微）→ 弱项热度图（TrainingWeakTagMap 换 HeatChip 网格）→ 任务列表（TrainingTaskList 行卡：状态 BrutChip 待开始 neutral/进行中 warn/已完成 ok）→ 练习面板（TrainingPracticePanel 用 BrutPanel + BrutField + BrutButton）。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign training page`

### Task 11: 复盘列表页（T2 台账）

**Files:** Modify: `frontend/src/pages/app/HistoryPage.vue`；Test: 既有 `history-page.test.ts` 保持绿

**结构规格：** 页题 28px；会话行 = 日期(mono) + 档案名 + 总分大数字(mono 900，score-5..1 档底色 ChunkChip 式) + 弱项 HeatChip 行 + BrutStamp 总评；行 2px 墨边 + `--shadow-3`；点击进入报告行为不变。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign history page`

### Task 12: 档案页（T2 身份卡）

**Files:** Modify: `frontend/src/pages/app/ProfilesPage.vue`、`frontend/src/components/profiles/*.vue`；Test: 既有 `profiles-page.test.ts` 保持绿

**结构规格：** 当前档案 = 大身份卡（公司/岗位/难度，激活蓝头 BrutPanel）；档案列表 = ProfileList 行卡 2px 墨边白底，激活项黄底；创建/编辑表单用 BrutField + BrutButton。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign profiles page`

### Task 13: 知识库页（T2 文档台账）

**Files:** Modify: `frontend/src/pages/app/KnowledgePage.vue`；Test: 既有 `knowledge-page.test.ts` 保持绿

**结构规格：** 上传区（BrutButton + BrutField）；文档台账行 = 标题 + 状态芯片（ready→ok"就绪"/processing→warn"处理中"/failed→danger"失败"，映射现有 status 值）+ 分块数(mono)；分块抽屉/查看区用 BrutPanel 行（命中分数用 ChunkChip）。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign knowledge page`

### Task 14: 设置页 + 后台页（T3 工具级）

**Files:** Modify: `frontend/src/pages/app/SettingsPage.vue`、`AdminPage.vue`；Test: 既有 `settings`/`admin-page.test.ts` 保持绿

**结构规格（T3 降档）：** 结构不动；scoped 样式全部收敛到令牌（旧 hex/rgba 全替换）；分节改 BrutPanel 黑头；按钮/芯片/状态换 Brut 同名替换（保持 data-testid 与事件）；投影只保留在交互元素上；表格行用发丝线。AdminPage 2141 行按 section 分块替换，不改模板结构。

- [ ] **Step 1-4:** 既有测试绿 → 重构 → 门禁 → 提交 `feat: redesign settings and admin pages (tier-3)`

### Task 15: 旧令牌清理 + 门禁扫描

**Files:** Modify: `frontend/src/styles/tokens.css`（删旧块）、全仓库 grep 清理

- [ ] **Step 1:** `grep -rn "color-accent\|color-surface\|color-text-muted\|shadow-soft\|radius-sm\|radius-md\|radius-lg" frontend/src/` 结果为 0（残留逐个改为新令牌）
- [ ] **Step 2:** 删除 tokens.css 旧块；`npx vitest run` + `npm run build` 全绿
- [ ] **Step 3:** 语义色审计：`grep -rn "#009639\|#ffd100\|#c8102e" frontend/src --include="*.vue"` 只允许出现在 tokens.css
- [ ] **Step 4:** 提交 `refactor: remove legacy design tokens`

### Task 16: 视觉验证（控制者执行，不派子代理）

- [ ] **Step 1:** `cd frontend && npx vite --host 127.0.0.1 --port 5173 &`（先探测端口）
- [ ] **Step 2:** Windows 无头 Chrome 逐页截图（登录/面试台/报告/训练/复盘/档案/知识库/设置/后台），Read+视觉分析工具自查每页：布局未碎、语义色就位、无旧样式残留
- [ ] **Step 3:** 发现的问题列清单回修（一轮批量），复查一次后停（bounded passes）
- [ ] **Step 4:** 提交修复（如有）`fix: visual polish after redesign`

### Task 17: README 更新

**Files:** Modify: `README.md`

- [ ] **Step 1:** 新增"设计系统"一节：令牌表（中性/动作/语义/数据梯度）+ 密度分级 T1/T2/T3 规则 + 语义色映射表（绿=合格 黄=护栏 红=不合格 蓝=指令/交互）
- [ ] **Step 2:** 前端截图段落替换为 Task 16 的截图（面试台 V2 为主图）
- [ ] **Step 3:** 提交 `docs: document the neo-brutalism design system`

### Task 18: 合并与 GitHub 推送（用户已预授权）

- [ ] **Step 1:** 确认 main 工作区干净、全量门禁最后跑一次
- [ ] **Step 2:** `git push origin main`（失败重试一次；仍失败走 gh-proxy 备选，参照 docs/roadmap/current-state.md 的推送记录）
- [ ] **Step 3:** 验证 `git log origin/main -1` 与本地一致

### Task 19: VPS 生产发布（用户已预授权；124.221.230.218 / ssh 别名 vps）

- [ ] **Step 1:** 探测服务器 node 环境：`ssh vps 'node -v && npm -v' || echo no-node`
- [ ] **Step 2a（有 node）:** `ssh vps 'cd ~/ai-interview && git pull && cd frontend && npm ci && npm run build'`
- [ ] **Step 2b（无 node）:** 本地 `cd frontend && npm run build` 后 `rsync -az frontend/dist/ vps:~/ai-interview/frontend/dist/`，并在服务器 `cd ~/ai-interview && git pull`
- [ ] **Step 3:** 健康门禁：`curl -s http://localhost:8000/api/health`（服务器内）与公网 `http://124.221.230.218/api/health` 均 200（纯前端变更，后端不动）
- [ ] **Step 4:** 公网抽查：`curl -s http://124.221.230.218/vue/ | head -5` 返回新构建的 index.html；无头 Chrome 截图公网面试台页面确认新皮肤上线
- [ ] **Step 5:** nginx 无需重启（纯静态内容变更）；如页面异常才按 runbook 重启（上游 DNS 缓存规则）
- [ ] **Step 6:** 回滚预案：发布前 `ssh vps 'cp -r ~/ai-interview/frontend/dist ~/dist-backup-$(date +%m%d)'`；异常时覆盖恢复
- [ ] **Step 7:** 在 docs/roadmap/current-state.md 记录本次发布（日期/提交/步骤结果）

---

## Self-Review 记录

- 规格覆盖：§2 令牌→Task 1/15；§3 组件 16 个→Task 2-5/7（QuestionStage/AnswerBox/RoundLedger 在 Task 7，其余 13 个在 Task 2-5）；§4 页面 12 页→Task 6-14；§5 密度分级→各页任务标注 T1/T2/T3；§6 动效→组件任务规范+Task 15 不审计动效（实现内建）；§7 红线→Global Constraints；§8 响应式→Task 8 及各页任务；§9 顺序→任务编号顺序；§10 发布→Task 18/19；§11 验收→Task 15/16 门禁 + Task 19 抽查；§12 风险→AdminPage T3（Task 14）、签名页先验收（Task 8 完成即可中检）
- 无占位符；组件 API 与页面任务引用名称一致（ModeSeg options 结构、RoundLedger rounds 结构在 Task 7 定义、Task 8 消费）
