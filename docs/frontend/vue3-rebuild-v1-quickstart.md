# Vue3 前端重构 V1 快速启动

## 1. 前端并行策略

旧前端继续保留：

```text
http://localhost:8000/
```

新 Vue3 前端开发期使用：

```text
http://localhost:5173/vue/
```

这样做的原因是：Vue3 重构期间不直接覆盖旧页面，旧页面仍然可以作为兜底入口。

## 2. 启动后端

```powershell
python -m uvicorn backend_python.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. 启动 Vue3 前端

```powershell
cd frontend
npm install
npm run dev
```

## 4. 验证入口

```text
旧页面：http://localhost:8000/
新页面：http://localhost:5173/vue/
登录页：http://localhost:5173/vue/auth/login
面试训练台：http://localhost:5173/vue/app/interview
```

## 5. 面试表达

这次前端重构采用新旧前端并行策略。旧原生页面继续保留，新 Vue3 页面使用 `/vue` 前缀独立运行。这样可以逐步迁移登录、档案、面试训练台、历史复盘和知识库页面，降低一次性替换带来的回归风险。
