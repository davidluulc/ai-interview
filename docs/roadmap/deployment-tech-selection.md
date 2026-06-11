# 上线技术选型

目标：把 AI 模拟面试系统从本地项目部署到云服务器，让别人可以通过公网访问。

## 当前项目状态

当前项目已经具备：

- 前端页面。
- Python FastAPI 后端。
- 阿里 Qwen 模型调用。
- PDF / 图片简历解析。
- 动态追问。
- 面试报告。
- 历史复盘。

但还缺少：
- 用户系统。
- 云服务器部署。
- 生产环境日志。
- HTTPS。
- 密钥管理。

## 推荐技术选型

### 前端

当前阶段继续使用：

```text
HTML + CSS + JavaScript
```

原因：

- 项目重点是 AI 后端和产品流程。
- 原生前端足够支撑当前 MVP。
- 先不引入 Vue / React，避免学习负担过重。

后续如果页面复杂，再考虑：

```text
Vue 或 React
```

### 后端

推荐使用：

```text
Python + FastAPI
```

原因：

- 你更熟悉 Python。
- FastAPI 适合写 API 接口。
- 后续接 RAG、数据处理、模型调用都更自然。
- 面试时更容易讲清楚。

### 数据库

开发阶段推荐：

```text
SQLite
```

原因：

- 简单。
- 不需要单独安装数据库服务。
- 适合保存用户、面试记录、报告。

上线阶段推荐：

```text
PostgreSQL
```

原因：

- 更适合生产环境。
- 以后可以配合向量扩展或独立向量库。

### ORM

推荐：

```text
SQLAlchemy
```

原因：

- Python 后端常用。
- 可以先连接 SQLite，后续切换 PostgreSQL。
- 适合面试讲解。

### 文件存储

MVP 阶段：

```text
不保存用户上传的原始简历
```

上线后如果要保存文件：

```text
阿里云 OSS
```

原因：

- 适合存 PDF、图片等对象文件。
- 不建议把用户文件直接存在服务器本地目录。

### 云服务器

推荐：

```text
阿里云 ECS
```

原因：

- 已经在用阿里百炼。
- 同一云厂商管理方便。
- 对国内访问更友好。

也可以选择：

```text
腾讯云 CVM
华为云 ECS
轻量应用服务器
```

### 部署方式

第一版推荐：

```text
Linux 云服务器 + Python venv + Uvicorn + Nginx
```

结构：

```text
用户浏览器 -> Nginx -> FastAPI/Uvicorn -> Qwen API
```

后续可以升级：

```text
Docker + Docker Compose
```

### HTTPS

推荐：

```text
Nginx + Certbot
```

用于给域名配置 HTTPS。

### 环境变量

敏感信息放在服务器 `.env`：

```text
DASHSCOPE_API_KEY=你的 key
QWEN_MODEL=qwen-plus
QWEN_VISION_MODEL=qwen-vl-plus
DATABASE_URL=sqlite:///./data/app.db
```

不要把 `.env` 提交到 Git。

## 推荐上线路线

### 第一步：本地加数据库

先用 SQLite 保存：

- 用户信息。
- 投递档案。
- 面试问题。
- 用户回答。
- 面试报告。

当前项目已经开始接入 SQLite，默认数据库文件：

```text
data/app.db
```

### 第二步：整理 FastAPI 后端

补充：

- 数据库模型。
- CRUD 接口。
- 错误处理。
- 日志。

### 第三步：部署到云服务器

流程：

1. 购买云服务器。
2. 安装 Python、Nginx、Git。
3. 拉取项目代码。
4. 配置 `.env`。
5. 启动 FastAPI。
6. 用 Nginx 反向代理。
7. 配置域名和 HTTPS。

### 第四步：后续增强

- 用户登录。
- RAG。
- 后台管理。
- 文件存储。
- 日志监控。

## 当前建议

下一步不要直接买服务器。

推荐先做：

```text
SQLite 数据库保存面试记录
```

原因：

- 这是上线前必须补的一环。
- 比直接部署更有项目价值。
- 面试时也更好讲。
