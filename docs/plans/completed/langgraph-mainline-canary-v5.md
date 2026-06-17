# LangGraph Mainline Canary V5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 LangGraph 从候选 runtime 进入可灰度的真实可见链路，同时保留 classic Agent 默认稳定链路和自动回退能力。

**Architecture:** 新增 runtime policy 和 runtime audit 两个纯函数层，先决定本轮是否允许 LangGraph 可见，再由 `agent_runtime.py` 执行 classic / shadow / langgraph_canary。`/api/interview/next-question` 只做兼容式字段扩展，不破坏旧前端调用。

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Pytest, Vue3, Pinia, Vitest, TypeScript.

---

## 0. 本轮要学的 Agent 工程化知识点

这一阶段学习的是 **Agent runtime 灰度迁移**。

你可以这样理解：

```text
classic Agent = 当前稳定主链路
LangGraph = 新候选链路
shadow = 后台偷偷对比，不影响用户
canary = 小范围可见，失败自动回退
quality gate = 质量门禁
runtime audit = 运行审计记录
```

本轮不是“框架接入”，而是“新 Agent 链路如何安全进入核心业务”。

## 1. 文件结构与职责

### 新增文件

- `backend_python/runtime_policy.py`
  - 判断本轮请求是否允许使用实验 runtime。
  - 不访问数据库，不调用模型。
  - 输出中文原因，便于后台解释。

- `backend_python/runtime_audit.py`
  - 汇总 policy、qualityGate、comparisonSummary、checkpointSummary。
  - 输出稳定的 `runtimeAudit` 字典。

- `tests/test_runtime_policy.py`
  - 覆盖普通用户、管理员、非法 runtime、coach/interview 模式策略。

- `tests/test_runtime_audit.py`
  - 覆盖可见链路、回退、质量门禁原因和 checkpoint 摘要。

### 修改文件

- `backend_python/agent_runtime.py`
  - 支持 `langgraph_canary`。
  - gate 通过时展示 LangGraph。
  - gate 失败时 fallback classic。
  - 返回 `runtimeAudit`。

- `backend_python/schemas.py`
  - `QuestionRequest` 增加可选 `agentRuntime`。

- `backend_python/routes/interview.py`
  - 主面试接口接入 runtime 偏好，但默认 classic。

- `backend_python/ai_debug.py`
  - normalizer 增加 runtimeAudit。

- `backend_python/routes/admin.py`
  - AI Debug detail 返回 runtimeAudit。

- `frontend/src/stores/interview.ts`
  - 增加实验 runtime 状态和请求字段。

- `frontend/src/pages/app/InterviewPage.vue`
  - 管理员展示 runtime 实验开关。

- `frontend/src/api/admin.ts`
  - 管理员调试类型增加 runtimeAudit。

- `frontend/src/pages/app/AdminPage.vue`
  - AI Debug 展示 runtime audit。

- `docs/roadmap/current-state.md`
  - 完成后更新当前路线。

- `docs/specs/README.md`
  - 更新 active spec 状态。

- `docs/plans/README.md`
  - 更新 active plan 状态。

---

## Task 1: Runtime Policy 纯函数

**Files:**
- Create: `tests/test_runtime_policy.py`
- Create: `backend_python/runtime_policy.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_runtime_policy.py`:

```python
from backend_python.runtime_policy import decide_runtime_policy


def test_default_runtime_is_classic_for_normal_user() -> None:
    policy = decide_runtime_policy(
        requested_runtime=None,
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "classic"
    assert policy["allowedRuntime"] == "classic"
    assert policy["canUseLangGraph"] is False
    assert policy["fallbackRuntime"] == "classic"
    assert "未请求实验链路，默认使用稳定 classic Agent" in policy["reasons"]


def test_normal_user_can_not_request_langgraph_canary() -> None:
    policy = decide_runtime_policy(
        requested_runtime="langgraph_canary",
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_canary"
    assert policy["allowedRuntime"] == "classic"
    assert policy["canUseLangGraph"] is False
    assert "普通用户暂不开放 LangGraph 灰度链路" in policy["reasons"]


def test_admin_can_request_langgraph_canary() -> None:
    policy = decide_runtime_policy(
        requested_runtime="langgraph_canary",
        user_role="admin",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_canary"
    assert policy["allowedRuntime"] == "langgraph"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True
    assert "管理员账号允许使用 LangGraph 灰度链路" in policy["reasons"]


def test_admin_shadow_still_uses_classic_as_visible_runtime() -> None:
    policy = decide_runtime_policy(
        requested_runtime="shadow",
        user_role="admin",
        agent_mode="interview",
    )

    assert policy["allowedRuntime"] == "shadow"
    assert policy["visibleRuntimeOnSuccess"] == "classic"
    assert policy["canUseLangGraph"] is True


def test_invalid_runtime_falls_back_to_classic() -> None:
    policy = decide_runtime_policy(
        requested_runtime="unknown",
        user_role="admin",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "unknown"
    assert policy["allowedRuntime"] == "classic"
    assert policy["canUseLangGraph"] is False
    assert "请求的 runtime 不合法，已降级为 classic" in policy["reasons"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_runtime_policy.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'backend_python.runtime_policy'
```

- [ ] **Step 3: 实现最小代码**

Create `backend_python/runtime_policy.py`:

```python
from __future__ import annotations

from typing import Any


VALID_REQUESTED_RUNTIMES = {"classic", "shadow", "langgraph_canary"}


def decide_runtime_policy(
    *,
    requested_runtime: str | None,
    user_role: str | None,
    agent_mode: str | None,
) -> dict[str, Any]:
    requested = (requested_runtime or "classic").strip() or "classic"
    role = (user_role or "user").strip().lower()
    mode = (agent_mode or "coach").strip().lower()
    reasons: list[str] = []

    if requested not in VALID_REQUESTED_RUNTIMES:
        return {
            "requestedRuntime": requested,
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["请求的 runtime 不合法，已降级为 classic"],
        }

    if requested == "classic":
        reasons.append("未请求实验链路，默认使用稳定 classic Agent")
        return {
            "requestedRuntime": "classic",
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": False,
            "agentMode": mode,
            "reasons": reasons,
        }

    if role != "admin":
        return {
            "requestedRuntime": requested,
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["普通用户暂不开放 LangGraph 灰度链路"],
        }

    if requested == "shadow":
        return {
            "requestedRuntime": "shadow",
            "allowedRuntime": "shadow",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": True,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["管理员账号允许使用 shadow 对比链路"],
        }

    return {
        "requestedRuntime": "langgraph_canary",
        "allowedRuntime": "langgraph",
        "fallbackRuntime": "classic",
        "visibleRuntimeOnSuccess": "langgraph",
        "visibleRuntimeOnFailure": "classic",
        "canUseLangGraph": True,
        "requiresAudit": True,
        "agentMode": mode,
        "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
python -m pytest tests/test_runtime_policy.py -q
```

Expected:

```text
5 passed
```

---

## Task 2: Runtime Audit 纯函数

**Files:**
- Create: `tests/test_runtime_audit.py`
- Create: `backend_python/runtime_audit.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_runtime_audit.py`:

```python
from backend_python.runtime_audit import build_runtime_audit


def test_runtime_audit_records_langgraph_success() -> None:
    audit = build_runtime_audit(
        policy={
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "fallbackRuntime": "classic",
            "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
        },
        quality_gate={"passed": True, "fallbackToClassic": False, "reasons": []},
        checkpoint_summary={"exists": True, "requiresHumanReview": False},
        comparison_summary={},
        visible_runtime="langgraph",
    )

    assert audit["requestedRuntime"] == "langgraph_canary"
    assert audit["allowedRuntime"] == "langgraph"
    assert audit["visibleRuntime"] == "langgraph"
    assert audit["fallbackUsed"] is False
    assert audit["qualityGatePassed"] is True
    assert audit["checkpointExists"] is True


def test_runtime_audit_records_fallback_reasons() -> None:
    audit = build_runtime_audit(
        policy={
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "fallbackRuntime": "classic",
            "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
        },
        quality_gate={
            "passed": False,
            "fallbackToClassic": True,
            "reasons": ["LangGraph 问题与最近问题重复度过高"],
        },
        checkpoint_summary={"exists": True, "requiresHumanReview": False},
        comparison_summary={},
        visible_runtime="classic",
    )

    assert audit["visibleRuntime"] == "classic"
    assert audit["fallbackUsed"] is True
    assert audit["qualityGatePassed"] is False
    assert audit["qualityGateReasons"] == ["LangGraph 问题与最近问题重复度过高"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_runtime_audit.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'backend_python.runtime_audit'
```

- [ ] **Step 3: 实现最小代码**

Create `backend_python/runtime_audit.py`:

```python
from __future__ import annotations

from typing import Any


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def build_runtime_audit(
    *,
    policy: dict[str, Any],
    quality_gate: dict[str, Any] | None,
    checkpoint_summary: dict[str, Any] | None,
    comparison_summary: dict[str, Any] | None,
    visible_runtime: str,
) -> dict[str, Any]:
    gate = quality_gate if isinstance(quality_gate, dict) else {}
    checkpoint = checkpoint_summary if isinstance(checkpoint_summary, dict) else {}
    comparison = comparison_summary if isinstance(comparison_summary, dict) else {}
    comparison_block = comparison.get("comparison") if isinstance(comparison.get("comparison"), dict) else {}

    fallback_used = bool(gate.get("fallbackToClassic") or comparison_block.get("fallbackToClassic") or visible_runtime == policy.get("fallbackRuntime"))

    return {
        "requestedRuntime": str(policy.get("requestedRuntime") or "classic"),
        "allowedRuntime": str(policy.get("allowedRuntime") or "classic"),
        "visibleRuntime": str(visible_runtime or "classic"),
        "fallbackRuntime": str(policy.get("fallbackRuntime") or "classic"),
        "fallbackUsed": fallback_used,
        "qualityGatePassed": bool(gate.get("passed", visible_runtime == "classic")),
        "qualityGateReasons": _string_list(gate.get("reasons")),
        "policyReasons": _string_list(policy.get("reasons")),
        "checkpointExists": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
        "requiresHumanReview": bool(checkpoint.get("requiresHumanReview")),
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
python -m pytest tests/test_runtime_audit.py -q
```

Expected:

```text
2 passed
```

---

## Task 3: Agent Runtime 接入 canary

**Files:**
- Modify: `tests/test_agent_runtime_switching.py`
- Modify: `backend_python/agent_runtime.py`

- [ ] **Step 1: 增加 canary 测试**

Add tests to `tests/test_agent_runtime_switching.py`:

```python
def test_langgraph_canary_uses_langgraph_when_quality_gate_passes() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "langgraph visible question"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_canary",
            thread_id="runtime-canary-pass",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 FastAPI？"]},
        )
    )

    assert result["runtime"] == "langgraph"
    assert result["visibleRuntime"] == "langgraph"
    assert result["question"]["content"] == "langgraph visible question"
    assert result["qualityGate"]["passed"] is True
    assert result["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert result["runtimeAudit"]["visibleRuntime"] == "langgraph"
    assert result["runtimeAudit"]["fallbackUsed"] is False


def test_langgraph_canary_falls_back_to_classic_when_quality_gate_fails() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": ""},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_canary",
            thread_id="runtime-canary-fail",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 RAG？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert result["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert result["runtimeAudit"]["visibleRuntime"] == "classic"
    assert result["runtimeAudit"]["fallbackUsed"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py -q
```

Expected:

```text
AssertionError 或 KeyError: runtimeAudit
```

- [ ] **Step 3: 修改 `agent_runtime.py`**

实现逻辑：

```text
if runtime == "langgraph_canary":
    run classic as fallback candidate
    run langgraph
    evaluate quality gate
    if gate passed:
        visible result = langgraph
        visibleRuntime = "langgraph"
    else:
        visible result = classic
        visibleRuntime = "classic"
    attach runtimeAudit
```

注意：

- 不删除原有 `classic`、`shadow`、`langgraph` 分支。
- `shadow` 仍然返回 classic 可见结果。
- 所有返回结构保留现有字段。
- `normalize_agent_runtime()` 需要把 `langgraph_canary` 加入合法 runtime 集合。
- `runtimeAudit` 由 `build_runtime_audit()` 生成。

- [ ] **Step 4: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_agent_runtime_switching.py tests/test_runtime_policy.py tests/test_runtime_audit.py -q
```

Expected:

```text
all selected tests passed
```

---

## Task 4: 主面试接口兼容 `agentRuntime`

**Files:**
- Modify: `backend_python/schemas.py`
- Modify: `backend_python/routes/interview.py`
- Modify: `tests/test_interview_agent_route.py`

- [ ] **Step 1: 写接口测试**

Add tests:

```python
def test_next_question_defaults_to_classic_when_agent_runtime_missing(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "FastAPI Depends",
                "reason": "候选人回答较短，先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "FastAPI Depends",
            "prompt": "我们先拆小一点：Depends 在 FastAPI 里解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-default-{suffix}@example.com"
    username = f"runtime_default_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "Python 后端开发实习生", "resume": "做过 FastAPI"},
            "history": [{"question": "Depends 是什么？", "answer": "依赖注入"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"]
    assert body["runtimeAudit"]["requestedRuntime"] == "classic"
    assert body["runtimeAudit"]["allowedRuntime"] == "classic"
    assert body["runtimeAudit"]["visibleRuntime"] == "classic"


def test_normal_user_langgraph_canary_request_is_downgraded(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "LangGraph 灰度",
                "reason": "普通用户请求实验链路时应由策略层降级。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "LangGraph 灰度",
            "prompt": "我们先解释一下：灰度发布为什么要保留 fallback？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-user-{suffix}@example.com"
    username = f"runtime_user_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "学习 LangGraph"},
            "history": [{"question": "LangGraph 是什么？", "answer": "工作流框架"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "langgraph_canary",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert body["runtimeAudit"]["allowedRuntime"] == "classic"
    assert body["runtimeAudit"]["visibleRuntime"] == "classic"
    assert "普通用户暂不开放 LangGraph 灰度链路" in body["runtimeAudit"]["policyReasons"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py -q
```

Expected:

```text
字段缺失或断言失败
```

- [ ] **Step 3: 修改 schema**

In `backend_python/schemas.py`, add optional field to `QuestionRequest`:

```python
agentRuntime: str | None = Field(default=None, description="Agent runtime preference: classic, shadow, or langgraph_canary")
```

- [ ] **Step 4: 修改 route**

In `backend_python/routes/interview.py`:

```text
读取 payload.agentRuntime
读取 current_user.role
调用 decide_runtime_policy()
当前第一步先保持主问题生成逻辑不大拆分：如果 policy.allowedRuntime 是 classic，则沿用现有 run_next_question_agent + call_model 流程。
如果 policy.allowedRuntime 是 shadow 或 langgraph，后续任务再把现有 classic 问题生成逻辑抽成 runner 并接入 run_agent_runtime。
把 runtimeAudit 合并进 response
```

保持旧字段不变。

- [ ] **Step 5: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_interview_agent_route.py tests/test_agent_runtime_switching.py -q
```

Expected:

```text
all selected tests passed
```

---

## Task 5: Vue3 面试页实验 runtime 开关

**Files:**
- Modify: `frontend/src/stores/interview.ts`
- Modify: `frontend/src/pages/app/InterviewPage.vue`
- Modify: related frontend tests under `frontend/src/pages/app/` and `frontend/src/stores/`

- [ ] **Step 1: 写前端测试**

测试目标：

```text
管理员能看到 runtime 实验开关。
普通用户看不到 runtime 实验开关。
选择 langgraph_canary 后 next-question payload 带 agentRuntime。
```

优先复用现有 auth store / interview store 测试模式。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts src/pages/app/interview-page.test.ts
```

Expected:

```text
找不到 runtime 开关或 payload 字段
```

- [ ] **Step 3: 实现 store 状态**

在 interview store 中增加：

```ts
agentRuntime: "classic" | "shadow" | "langgraph_canary";
setAgentRuntime(runtime: "classic" | "shadow" | "langgraph_canary"): void;
```

请求 next question 时带上：

```ts
agentRuntime: state.agentRuntime
```

- [ ] **Step 4: 实现页面开关**

在 `InterviewPage.vue` 中：

```text
仅管理员显示实验 runtime segmented control。
选项：稳定链路、旁路对比、LangGraph 灰度。
显示一行轻量说明。
```

不要把后台调试 JSON 暴露给普通用户。

- [ ] **Step 5: 运行前端 focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/interview.test.ts src/pages/app/interview-page.test.ts
```

Expected:

```text
all selected tests passed
```

---

## Task 6: AI Debug 展示 Runtime Audit

**Files:**
- Modify: `backend_python/ai_debug.py`
- Modify: `backend_python/routes/admin.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: 写后端和前端测试**

覆盖：

```text
normalize_checkpoint 或 AI Debug detail 包含 runtimeAudit。
AdminPage 显示 请求链路、允许链路、可见链路、Fallback。
页面无 undefined。
```

- [ ] **Step 2: 实现后端字段透传**

在 AI Debug normalizer 中加入：

```python
"runtimeAudit": checkpoint.get("runtimeAudit") if isinstance(checkpoint.get("runtimeAudit"), dict) else {}
```

- [ ] **Step 3: 实现前端展示**

管理员后台新增小节：

```text
Runtime 审计
请求链路
允许链路
可见链路
Fallback
策略原因
门禁原因
```

- [ ] **Step 4: 运行 focused tests**

Run:

```powershell
python -m pytest tests/test_admin_ai_debug.py -q
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected:

```text
all selected tests passed
```

---

## Task 7: 文档、路线与全量验证

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Create: `docs/learning/24-LangGraph主链路灰度迁移怎么讲.md`

- [ ] **Step 1: 写学习文档**

学习文档必须解释：

- classic / shadow / canary 的区别。
- quality gate 的作用。
- fallback classic 的作用。
- runtime audit 的作用。
- 为什么这比直接替换主链路更专业。
- 面试时怎么讲。

- [ ] **Step 2: 全量后端测试**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: 全量前端测试**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected:

```text
all tests passed
```

- [ ] **Step 4: 前端 build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected:

```text
built successfully
```

- [ ] **Step 5: 浏览器验证**

Open:

```text
http://127.0.0.1:5173/vue/app/interview
http://127.0.0.1:5173/vue/app/admin
```

Verify:

```text
管理员能看到实验 runtime 开关。
普通用户看不到实验 runtime 开关。
管理员后台能看到 Runtime 审计。
页面没有 undefined。
移动端没有横向溢出。
```

- [ ] **Step 6: 完成归档**

验证通过后：

```powershell
Move-Item docs\specs\active\langgraph-mainline-canary-v5-design.md docs\specs\completed\langgraph-mainline-canary-v5-design.md
Move-Item docs\plans\active\langgraph-mainline-canary-v5.md docs\plans\completed\langgraph-mainline-canary-v5.md
```

更新：

```text
docs/specs/README.md
docs/plans/README.md
docs/roadmap/current-state.md
```

---

## Self-Review

### Spec coverage

- Runtime 灰度策略：Task 1 覆盖。
- Runtime 审计：Task 2、Task 6 覆盖。
- Agent Runtime canary：Task 3 覆盖。
- 主接口兼容扩展：Task 4 覆盖。
- Vue3 面试页实验开关：Task 5 覆盖。
- AI Debug 可观测：Task 6 覆盖。
- 学习文档与路线更新：Task 7 覆盖。

### Placeholder scan

本计划没有保留 `TODO`、`TBD` 或 `pass` 占位代码。涉及现有复杂 route 和前端 store 的任务，均要求先用当前文件里的 fixture 和 mock 风格扩展测试，再写实现。

### Type consistency

统一字段名：

- `agentRuntime`
- `runtimeAudit`
- `requestedRuntime`
- `allowedRuntime`
- `visibleRuntime`
- `fallbackRuntime`
- `fallbackUsed`
- `qualityGatePassed`
- `qualityGateReasons`
- `policyReasons`
