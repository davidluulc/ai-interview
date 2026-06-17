# Vue3 前端重构 V1 设计

## 1. 文档目的

本文档用于规划 AI 模拟面试系统下一阶段的前端重构：在不破坏现有 FastAPI、RAG、Agent、LangGraph、Docker/Nginx 部署基线的前提下，引入 Vue3 前端工程化体系，把当前原生 HTML / CSS / JavaScript 单页应用逐步升级为更像真实产品的前后端分离前端。

本阶段不是简单“把页面换成 Vue3”，而是建立一套可以继续演进的前端结构：

```text
Vue3 + Vite + TypeScript
-> Vue Router 页面路由
-> Pinia 管理登录态和核心业务状态
-> API client 统一封装后端请求
-> 极简、克制、接近苹果式审美的产品视觉
-> 保留旧原生页面作为兜底入口
```

面试表达目标：

```text
项目早期为了快速验证业务，前端采用原生 HTML/CSS/JS 实现。随着功能增加，单页结构开始变重，所以我把前端重构为 Vue3 + Vite + TypeScript 的工程化项目，通过 Vue Router 拆分页面，通过 Pinia 管理登录态和业务状态，通过 API client 统一对接 FastAPI。重构时没有一次性删除旧页面，而是采用新旧前端并行的渐进式迁移，降低风险。
```

## 2. 当前前端状态

当前前端已经具备较完整的业务能力，但结构仍然偏 MVP：

- `index.html` 承载大部分页面结构。
- `styles.css` 承载全局样式。
- `app.js` 承载登录、档案、面试、RAG、Agent、训练、后台等大量交互逻辑。
- 前端测试位于 `tests/frontend_*.test.mjs`。
- FastAPI 当前直接返回 `index.html`、`styles.css`、`app.js`。

已具备的产品模块：

- 登录 / 注册 / token 刷新。
- 面试训练工作台。
- 投递档案。
- 简历入口。
- RAG 文档管理。
- RAG debug / 命中日志。
- Agent 决策日志。
- 历史复盘。
- 训练中心。
- 管理员后台入口。

主要问题：

- 单页堆叠感强，页面边界不够清晰。
- `app.js` 体积大，状态和 UI 操作耦合。
- 视觉已经有阶段性改善，但还不够像正式产品。
- 用户端、知识库、历史复盘、管理后台混在一个页面里，后续维护成本会继续上升。

## 3. 本阶段目标

### 3.1 三个目标同时满足，但分优先级推进

本次重构同时追求三类价值：

1. 视觉展示：让项目更适合演示、截图、写简历。
2. 前端工程化：让项目具备 Vue3、路由、状态管理、API 封装、组件化能力。
3. 产品体验：让面试训练、投递档案、报告复盘、知识库管理更顺手。

优先级顺序：

```text
先保证主流程能跑通
-> 再保证页面结构清晰
-> 再打磨视觉和交互动效
-> 最后迁移全部后台和调试能力
```

### 3.2 V1 阶段完成边界

V1 重点做：

- 新建 `frontend/` Vue3 工程。
- 使用 Vite 作为前端构建工具。
- 使用 TypeScript。
- 使用 Vue Router 拆分页面。
- 使用 Pinia 管理登录态、用户信息、当前档案、面试会话等状态。
- 封装 API client。
- 设计极简产品框架。
- 接通登录、注册、当前用户、投递档案列表、面试训练主流程。
- 保留旧页面入口，不直接删除 `index.html` / `styles.css` / `app.js`。
- 通过 FastAPI 或 Nginx 预留 Vue3 构建产物访问方式。

V1 暂不做：

- 不重构后端 API。
- 不重构 RAG、Agent、LangGraph。
- 不替换 LangGraph 主流程。
- 不做真实移动 App。
- 不做复杂动画和营销型首页。
- 不删除旧前端。
- 不一次性迁移所有管理后台能力。
- 不引入重型 UI 组件库导致默认后台风格过重。

## 4. 技术选型

推荐技术栈：

```text
Vue3
Vite
TypeScript
Vue Router
Pinia
Axios 或原生 fetch 封装
Vitest
Playwright 或现有 .mjs 测试补充
```

样式策略：

```text
优先使用自定义 CSS 变量 + 组件级样式
可以评估 Tailwind CSS，但 V1 不强制引入
不优先引入 Element Plus、Ant Design Vue 等重后台组件库
```

原因：

- Vue3 更贴近国内中小公司前端技术栈，适合求职表达。
- Vite 启动快，配置轻，适合当前项目。
- TypeScript 能提高接口数据结构表达能力。
- Pinia 是 Vue3 常用状态管理方案，比把所有状态放组件里更清晰。
- 自定义样式更容易做出极简、克制、接近苹果官网的视觉，而不是默认后台系统味。

## 5. 视觉风格

用户期望风格：

```text
极简、干净、克制、类似苹果官网的高级感
```

项目最终风格应为：

```text
苹果式极简视觉 + SaaS 工作台信息结构
```

具体规则：

- 浅色优先。
- 黑、白、灰作为主色。
- 使用低饱和蓝色作为强调色。
- 大面积留白，但工作台区域不能过空。
- 字体层级清楚。
- 弱边框、弱阴影、低噪声背景。
- 圆角适中，不做过度圆润的玩具感。
- 卡片只用于具体内容容器，不做大量套娃卡片。
- 动效克制，只用于页面切换、按钮反馈、面板展开。
- 首页、登录页、报告页可以更接近苹果官网的留白和高级感。
- 面试训练台、知识库、后台页面更接近专业 SaaS 工具。

不做：

- 不做大面积紫蓝渐变。
- 不做装饰性光斑、漂浮球、复杂背景。
- 不做纯营销落地页，把核心训练功能藏起来。
- 不做密密麻麻的传统后台模板。

## 6. 页面结构

### 6.1 路由设计

建议路由：

```text
/vue
/vue/auth/login
/vue/auth/register

/vue/app/interview
/vue/app/profiles
/vue/app/knowledge
/vue/app/history
/vue/app/training
/vue/app/admin
/vue/app/settings
```

说明：

- 先使用 `/vue` 前缀，避免直接覆盖旧首页。
- 旧页面继续保留在 `/`。
- Vue3 稳定后，再评估是否将 `/` 切换到 Vue3。

### 6.2 页面分区

用户端：

- 登录注册页。
- 面试训练台。
- 投递档案页。
- 历史复盘页。
- 训练中心页。

知识库：

- 知识库总览。
- 岗位知识库。
- 题库。
- 候选人画像。
- 文档详情。
- 检索测试。
- RAG 质量评估。

管理员后台：

- 后台首页。
- 用户列表。
- RAG 文档概览。
- RAG 命中日志。
- Agent 决策日志。
- 系统配置只读查看。

V1 优先迁移：

```text
登录注册
当前用户
投递档案列表
面试训练台主流程
历史复盘入口
```

V2 再迁移：

```text
完整历史复盘
训练中心
知识库管理
RAG debug
Agent 日志
管理员后台
```

## 7. 核心交互逻辑

### 7.1 主使用流程

推荐主流程：

```text
用户登录
-> 创建或选择投递档案
-> 填写简历、岗位 JD、公司、目标岗位
-> 进入面试训练台
-> AI 面试官基于档案、RAG、Agent state 提问
-> 用户回答
-> 右侧展示 Agent 决策摘要和 RAG 命中摘要
-> 面试结束生成报告
-> 报告沉淀弱点标签和训练建议
-> 用户进入训练中心做专项训练
```

### 7.2 面试训练台布局

建议采用：

```text
顶部：产品名、当前用户、模式切换、退出
左侧：当前档案、面试设置、历史入口
中间：面试聊天主区域
右侧：Agent 决策、RAG 命中、能力画像
底部：回答输入框、提交、跳过、结束面试
```

交互规则：

- 中间聊天区永远是主视觉。
- Agent 和 RAG 解释默认折叠或弱化，不抢主流程。
- 用户可以展开查看“为什么这么问”。
- 回答提交时显示明确 loading 状态。
- 接口失败时给出可理解提示，不直接暴露后端堆栈。
- token 过期时尝试自动刷新，失败后回到登录页。

### 7.3 投递档案页

投递档案是面试训练的起点。

字段建议：

- 标题。
- 目标岗位。
- 公司。
- 岗位 JD。
- 简历文本。
- 投递类型。
- 标签。
- 创建时间 / 更新时间。

交互规则：

- 用户可以创建、编辑、选择档案。
- 面试训练台必须绑定一个当前档案。
- 没有档案时，引导用户先创建档案。

### 7.4 知识库页面

V1 可以只做入口和只读总览，V2 再完整迁移。

长期交互：

```text
选择知识库类型
-> 查看文档列表
-> 查看文档状态和 chunk 数
-> 新增/停用/归档文档
-> 执行检索测试
-> 查看 RAG 命中解释和质量评估
```

### 7.5 管理后台

管理员后台不应抢占用户端主体验。

V1 只保留入口或只读概览。
V2/V3 再迁移完整后台。

## 8. 前端架构

建议目录结构：

```text
frontend/
  package.json
  index.html
  vite.config.ts
  tsconfig.json
  src/
    main.ts
    App.vue
    router/
      index.ts
    stores/
      auth.ts
      profile.ts
      interview.ts
    api/
      client.ts
      auth.ts
      profiles.ts
      interview.ts
      history.ts
    layouts/
      AuthLayout.vue
      AppLayout.vue
    pages/
      auth/
        LoginPage.vue
        RegisterPage.vue
      app/
        InterviewPage.vue
        ProfilesPage.vue
        KnowledgePage.vue
        HistoryPage.vue
        TrainingPage.vue
        AdminPage.vue
        SettingsPage.vue
    components/
      common/
      interview/
      profile/
      rag/
      agent/
    styles/
      tokens.css
      base.css
```

边界原则：

- `api/` 只负责请求后端。
- `stores/` 只负责跨页面状态。
- `pages/` 负责页面编排。
- `components/` 负责可复用 UI。
- 业务复杂逻辑不要全部塞进组件。

## 9. API 对接策略

本阶段不改后端 API。

Vue3 前端通过统一 API client 调用现有接口：

- 登录。
- 注册。
- 刷新 token。
- 当前用户。
- 投递档案。
- 面试下一题。
- 历史记录。
- 报告保存。
- RAG 和 Agent 日志。

API client 需要统一处理：

- baseURL。
- access token 注入。
- 401 自动 refresh。
- refresh 失败后清理登录态。
- JSON 请求和响应。
- 错误提示结构化。

## 10. 新旧前端并行策略

本阶段明确保留旧页面。

并行方式：

```text
/             -> 旧 index.html
/styles.css   -> 旧 styles.css
/app.js       -> 旧 app.js
/vue/...      -> 新 Vue3 前端
```

好处：

- Vue3 开发过程中旧功能仍可使用。
- 遇到 Vue3 未迁移功能，可以跳回旧页面。
- 便于逐页迁移和对照测试。
- 降低一次性替换造成的大面积回归风险。

切换入口的条件：

- Vue3 登录注册稳定。
- Vue3 面试主流程稳定。
- Vue3 投递档案稳定。
- Vue3 历史复盘至少具备基础查看能力。
- 后端全量 pytest 通过。
- Vue3 前端测试通过。
- 浏览器桌面和移动端检查通过。

满足后再评估：

```text
/ -> Vue3
/legacy -> 旧页面
```

## 11. 测试策略

### 11.1 前端单元测试

建议使用 Vitest 覆盖：

- API client token 注入。
- 401 refresh 逻辑。
- auth store 登录态。
- profile store 当前档案。
- interview store 会话状态。

### 11.2 页面级测试

可以继续保留现有 `.mjs` 测试，并逐步新增 Vue3 对应测试。

关键路径：

- 未登录访问 `/vue/app/interview` 会跳转登录。
- 登录成功后进入面试训练台。
- 无投递档案时提示创建档案。
- 创建档案后可以进入面试。
- 提交回答后能渲染下一题或错误提示。
- token 过期可以 refresh。
- refresh 失败回到登录页。

### 11.3 浏览器验证

每轮 UI 改动后验证：

- 桌面端。
- 移动端。
- 登录页。
- 面试训练台。
- 投递档案页。
- 错误状态和 loading 状态。

## 12. 部署和构建策略

V1 可以先采用开发期双服务：

```text
FastAPI: http://localhost:8000
Vue Vite dev server: http://localhost:5173
```

后续生产构建：

```text
frontend npm run build
-> 生成 frontend/dist
-> FastAPI 或 Nginx 提供静态资源
```

Docker 后续适配：

- Dockerfile 增加前端构建阶段，或使用独立前端镜像。
- Nginx 配置支持 Vue history fallback。
- `/api/` 继续反向代理到 FastAPI。
- Vue3 静态资源由 Nginx 提供。

V1 不强制一次性完成 Docker 前端构建集成，但 spec 中保留方向。

## 13. 风险和控制

### 13.1 范围膨胀

风险：

```text
Vue3 重构时顺手改后端、改 RAG、改 Agent、改 LangGraph，导致阶段失控。
```

控制：

- V1 不改后端 API。
- V1 不动 RAG/Agent/LangGraph 主流程。
- 只通过 API client 对接现有接口。

### 13.2 旧功能丢失

风险：

```text
Vue3 页面没迁移完整，旧页面又被删掉，导致功能退化。
```

控制：

- 旧页面保留。
- Vue3 使用 `/vue` 前缀。
- 每迁移一个模块，写测试确认主流程。

### 13.3 视觉过度营销化

风险：

```text
为了像苹果官网，做成大字大图的宣传页，反而不适合训练工具。
```

控制：

- 首页、登录页、报告页可以更极简。
- 面试训练台和后台必须保持工具效率。
- 视觉服务于使用流程。

### 13.4 学习成本过高

风险：

```text
一次性引入 Vue3、TypeScript、Pinia、Router、测试、组件库，用户学习压力过大。
```

控制：

- 分阶段讲解。
- 每轮开发前先解释一个前端知识点。
- 第一阶段只跑通核心结构和主流程。

## 14. 验收标准

V1 完成时必须满足：

- `frontend/` Vue3 工程存在。
- 可以启动 Vue3 dev server。
- 可以访问 `/vue/auth/login` 或对应开发路由。
- 登录注册页面具备极简视觉。
- 登录态可以保存和恢复。
- API client 能调用现有 FastAPI。
- 面试训练主页面可以展示当前档案和聊天区。
- 旧 `/` 页面仍然可用。
- 不破坏现有后端测试。
- 不破坏现有前端 `.mjs` 测试。
- 新增 Vue3 相关测试或最小验证脚本。
- 文档说明如何启动旧前端和新 Vue3 前端。

建议验证命令：

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

如果引入 `frontend/package.json`，还需要：

```powershell
cd frontend
npm install
npm run test
npm run build
```

## 15. 分阶段路线

推荐路线：

```text
Vue3 V1：产品壳 + 登录态 + 面试主流程
Vue3 V2：投递档案 / 历史 / 报告 / 训练中心
Vue3 V3：知识库 / RAG / Agent 日志 / 管理后台
Vue3 V4：视觉精修 + 动效 + 移动端适配 + 入口切换
```

本 spec 只覆盖 V1。

后续如果 V1 稳定，再为 V2/V3/V4 分别写独立 spec 和 plan。

## 16. 下一步

用户确认本文档后，下一步编写 implementation plan，计划内容应包含：

- 初始化 Vue3 工程。
- 设计基础视觉 token。
- 搭建路由和布局。
- 封装 API client。
- 实现 auth store。
- 实现登录注册页。
- 实现 AppLayout。
- 实现面试训练台 V1。
- 保留旧页面。
- 补充测试和启动文档。
