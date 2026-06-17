# Project Directory Cleanup V1 设计文档

更新时间：2026-06-14

## 1. 背景

当前项目已经从早期的原生 HTML / CSS / JavaScript 前端，逐步升级到了 Vue3 + Vite + TypeScript 前端。

但项目根目录里仍然同时存在两套前端入口：

```text
index.html
styles.css
app.js
```

以及：

```text
frontend/
```

用户双击 `start-python-server.cmd` 后，启动的是 FastAPI 后端：

```text
python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload
```

因此浏览器访问 `http://localhost:8000/` 时，会进入旧版原生前端页面，而不是当前重点开发的 Vue3 页面。

Vue3 新前端的开发入口是：

```text
http://localhost:5173/vue/
```

这会造成几个问题：

- 用户容易误以为项目“打开错了”。
- 根目录文件较多，主入口不清晰。
- 旧前端、Vue3 前端、后端、部署文件混在同一层级里。
- README 仍然带有旧阶段内容，和当前项目状态不完全一致。
- 后续如果直接删除旧前端，可能破坏历史测试、部署入口或文档引用。

所以本阶段目标不是“大清理”，而是先做一轮低风险目录治理，让项目入口更清晰。

## 2. 本阶段目标

Project Directory Cleanup V1 的目标是：

```text
明确主前端入口为 frontend/ Vue3 应用，
明确根目录 index.html / styles.css / app.js 是 legacy 旧前端，
整理启动脚本和 README，
避免用户再次误开旧页面。
```

具体目标：

1. 新增清晰启动脚本：
   - `start-backend.cmd`
   - `start-vue-frontend.cmd`
   - 可选：`start-dev.cmd`
2. 保留 `start-python-server.cmd`，但标记为旧命名兼容入口。
3. README 更新为当前真实技术栈和启动方式。
4. 根目录旧前端文件暂不删除，先迁移或标记为 legacy。
5. 明确访问地址：
   - 后端 API 文档：`http://127.0.0.1:8000/docs`
   - 后端健康检查：`http://127.0.0.1:8000/api/health`
   - Vue3 前端：`http://127.0.0.1:5173/vue/app/interview`
6. 更新路线文档，说明当前 active 阶段是目录治理 V1。

## 3. 非目标

本阶段不做：

- 不重写后端 API。
- 不重写 Vue3 前端页面。
- 不删除数据库文件。
- 不删除日志文件。
- 不改 Docker / Nginx / VPS 部署链路。
- 不做真实云服务器上线。
- 不改 RAG、Agent、LangGraph 主流程。
- 不一次性清空所有历史文档。
- 不强行删除旧前端测试。

尤其注意：

```text
index.html / styles.css / app.js 暂时不能直接删除。
```

原因是历史 `.mjs` 前端测试、旧文档和部分部署说明仍然引用它们。直接删除会让项目状态变得不稳定。

## 4. 当前目录问题

当前根目录大致是：

```text
新项目/
  backend_python/
  frontend/
  docs/
  tests/
  scripts/
  logs/
  data/
  deploy/
  alembic/
  index.html
  styles.css
  app.js
  start-python-server.cmd
  README.md
  requirements.txt
  Dockerfile
  docker-compose.yml
```

这里的问题不是“文件太多”本身，而是职责边界不清：

- `backend_python/` 是后端。
- `frontend/` 是 Vue3 新前端。
- `index.html / styles.css / app.js` 是旧前端。
- `start-python-server.cmd` 只启动后端，但名字不提示“只启动后端”。
- 用户双击启动后，容易在浏览器里打开 `localhost:8000`，进入旧前端。

## 5. 建议目标结构

本阶段整理后建议形成：

```text
新项目/
  backend_python/              # FastAPI 后端
  frontend/                    # Vue3 + Vite 前端，当前主前端
  legacy_frontend/             # 旧原生前端，保留用于兼容和历史对照
    index.html
    styles.css
    app.js
    README.md
  docs/                        # 文档
  tests/                       # 后端测试和旧前端 .mjs 测试
  scripts/                     # 脚本
  data/                        # 本地数据
  logs/                        # 本地日志
  deploy/                      # 部署配置
  alembic/                     # 数据库迁移
  start-backend.cmd            # 启动 FastAPI 后端
  start-vue-frontend.cmd       # 启动 Vue3 前端
  start-dev.cmd                # 可选，同时提示如何启动两端
  start-python-server.cmd      # 兼容旧入口，内部调用 start-backend.cmd
  README.md                    # 当前项目说明
  requirements.txt
  Dockerfile
  docker-compose.yml
```

如果第一轮担心移动旧前端会影响测试，可以采用更保守方案：

```text
保留 index.html / styles.css / app.js 在根目录
新增 legacy_frontend/README.md 说明旧前端身份
先不移动旧文件
```

推荐做法是先走保守方案，再在后续 V2 中迁移旧前端文件。

## 6. 启动入口设计

### 6.1 后端启动

新增：

```text
start-backend.cmd
```

职责：

```text
启动 FastAPI 后端，监听 127.0.0.1:8000
```

用户看到的提示应该明确：

```text
Backend API:
http://127.0.0.1:8000/docs

Health Check:
http://127.0.0.1:8000/api/health

Vue frontend is NOT served here during local development.
Please run start-vue-frontend.cmd and open http://127.0.0.1:5173/vue/app/interview
```

### 6.2 Vue3 前端启动

新增：

```text
start-vue-frontend.cmd
```

职责：

```text
进入 frontend/，执行 npm.cmd run dev
```

用户看到的提示应该明确：

```text
Vue3 frontend:
http://127.0.0.1:5173/vue/app/interview
```

### 6.3 旧脚本兼容

保留：

```text
start-python-server.cmd
```

但建议改成：

```text
call start-backend.cmd
```

并在文件开头提示：

```text
This is a legacy script name. Prefer start-backend.cmd.
```

这样不会破坏用户已有习惯，也能逐步把启动心智迁移到新脚本。

## 7. README 更新设计

README 应该改成当前项目真实说明，而不是早期 MVP 状态。

建议结构：

```text
# AI 模拟面试系统

## 项目简介
## 当前主技术栈
## 本地启动方式
  1. 启动后端
  2. 启动 Vue3 前端
  3. 登录演示账号
## 目录结构
## 旧前端说明
## 常用命令
## 测试命令
## 后续路线
```

重点要讲清：

```text
http://127.0.0.1:8000/ 是旧前端或后端根入口，不是当前主页面。
当前主页面是 Vue3 前端：http://127.0.0.1:5173/vue/app/interview
```

## 8. 旧前端处理策略

旧前端目前仍然有价值：

- 可以作为早期版本对照。
- 有部分 `.mjs` 测试仍然读取 `app.js`、`styles.css`、`index.html`。
- 某些历史文档仍然引用旧入口。
- 后端 `http://localhost:8000/` 当前可能仍返回它。

因此 V1 不建议强删。

推荐策略：

```text
V1：标记 legacy，更新 README 和启动脚本，避免误用。
V2：扫描旧前端测试和后端静态文件挂载，再决定是否迁移到 legacy_frontend/。
V3：如果 Vue3 build 可以被 FastAPI 或 Nginx 稳定托管，再考虑让 8000 根路径跳转到 Vue3。
```

## 9. 测试与验证

本阶段如果只新增脚本和文档，主要验证：

```powershell
Test-Path .\start-backend.cmd
Test-Path .\start-vue-frontend.cmd
Test-Path .\README.md
```

如果修改脚本，需要验证：

```powershell
.\start-backend.cmd
```

打开：

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/health
```

前端验证：

```powershell
.\start-vue-frontend.cmd
```

打开：

```text
http://127.0.0.1:5173/vue/app/interview
```

如果移动旧前端文件，则必须额外运行：

```powershell
node tests/frontend_product_navigation.test.mjs
node tests/frontend_workbench_layout.test.mjs
```

以及所有仍引用根目录旧前端的 `.mjs` 测试。

## 10. 风险与控制

### 风险 1：移动旧前端导致测试失败

控制方式：

```text
V1 不强行移动旧前端文件。
如果要移动，先改测试路径，再运行相关 .mjs 测试。
```

### 风险 2：用户误以为 8000 是新前端

控制方式：

```text
README 和启动脚本提示里明确 8000 是后端 API，5173 是 Vue3 前端。
```

### 风险 3：根目录仍然看起来不够清爽

控制方式：

```text
先处理入口认知，再处理物理迁移。
目录治理分 V1 / V2，不一口气大搬家。
```

## 11. 完成标准

V1 完成时应满足：

- `docs/specs/active/project-directory-cleanup-v1-design.md` 存在。
- 新增或更新启动脚本说明，让后端和 Vue3 前端入口清晰。
- README 明确当前主前端是 `frontend/` Vue3 应用。
- README 明确 `localhost:8000` 和 `localhost:5173` 的区别。
- 不破坏现有后端启动。
- 不破坏 Vue3 前端启动。
- 不直接删除旧前端。
- 路线文档指向当前目录治理阶段。

## 12. 面试时怎么讲

可以这样讲：

```text
项目早期是原生 HTML/CSS/JS 前端，后来逐步迁移到 Vue3 + Vite + TypeScript。为了避免新旧入口混淆，我做了一轮目录治理：明确 backend_python 是 FastAPI 后端，frontend 是当前主前端，旧的 index.html / app.js / styles.css 标记为 legacy；同时拆分后端和前端启动脚本，并在 README 里明确 8000 是后端 API，5173 是 Vue3 前端开发入口。

这不是简单删文件，而是渐进式迁移。因为旧前端还有历史测试和文档引用，所以我先通过脚本和文档降低误用风险，再规划后续迁移 legacy_frontend。
```
