# Question Review Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a learning-oriented per-question review to generated reports and history review pages.

**Architecture:** Keep the existing report JSON storage model and extend the report payload with `questionReviews`. Backend report generation will normalize model output and create deterministic fallback reviews when the model omits them. Frontend report rendering and history rendering will share helper functions so current reports and saved reports show the same learning review structure.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest, vanilla JavaScript, Node-based frontend tests.

---

## File Structure

- Modify `backend_python/prompts/interview.py`: update the report system prompt to request `questionReviews`.
- Modify `backend_python/routes/interview.py`: add small review normalization helpers and include `questionReviews` in `/api/interview/report`.
- Modify `app.js`: render `questionReviews` on the current report and history review pages, with fallback to existing answer list for old records.
- Modify `tests/test_rag_retrieval_logs.py` or create `tests/test_question_reviews.py`: backend tests for report review preservation and fallback.
- Modify `tests/frontend_history_review.test.mjs`: verify history review renders `questionReviews`.
- Modify `tests/frontend_interview_flow.test.mjs` or create a focused frontend test: verify current report renders `questionReviews`.
- Modify `index.html`: bump the `app.js` query version after frontend changes.

## Task 1: Backend Report Review Fallback

**Files:**
- Modify: `backend_python/routes/interview.py`
- Test: `tests/test_question_reviews.py`

- [ ] **Step 1: Write failing backend tests**

Create `tests/test_question_reviews.py`:

```python
import time

from fastapi.testclient import TestClient

from backend_python.main import app


client = TestClient(app)


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def register_and_login(email: str, username: str) -> dict:
    password = "ExamplePass123!"
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def test_report_builds_question_reviews_when_model_omits_them(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        return {
            "score": 50,
            "strengths": ["能说明部分概念"],
            "risks": ["回答过短"],
            "actions": ["补充项目例子"],
        }

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-fallback-{suffix}@example.com", f"review_fb_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "targetRole": "Python AI 应用实习生",
                "resume": "做过 FastAPI 和 RAG 日志",
                "jd": "需要理解 RAG 和后端接口",
                "companyNeeds": "重视学习能力",
            },
            "answers": [
                {
                    "stage": "技术追问",
                    "focus": "RAG 召回链路",
                    "question": "请解释 RAG 命中日志怎么设计？",
                    "answer": "不知道",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questionReviews"][0]["index"] == 1
    assert body["questionReviews"][0]["focus"] == "RAG 召回链路"
    assert body["questionReviews"][0]["answerStatus"] == "不会"
    assert "RAG 命中日志" in body["questionReviews"][0]["question"]
    assert body["questionReviews"][0]["trainingAction"]


def test_report_preserves_model_question_reviews(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        return {
            "score": 80,
            "strengths": ["表达清楚"],
            "risks": ["细节略少"],
            "actions": ["补充指标"],
            "questionReviews": [
                {
                    "index": 1,
                    "focus": "后端模块设计",
                    "question": "你怎么拆 FastAPI 模块？",
                    "answerStatus": "模糊",
                    "whyAsked": "用于确认你是否理解模块边界。",
                    "missingPoints": ["路由层职责", "服务层职责"],
                    "referenceDirection": "按 router、service、model、schema 的顺序讲。",
                    "trainingAction": "画一张后端模块调用图。",
                }
            ],
        }

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-preserve-{suffix}@example.com", f"review_ps_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "Python 后端实习生"},
            "answers": [
                {
                    "stage": "技术问答",
                    "focus": "后端模块设计",
                    "question": "你怎么拆 FastAPI 模块？",
                    "answer": "按路由和模型拆。",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questionReviews"][0]["whyAsked"] == "用于确认你是否理解模块边界。"
    assert body["questionReviews"][0]["missingPoints"] == ["路由层职责", "服务层职责"]
```

- [ ] **Step 2: Run backend tests to verify RED**

Run: `python -m pytest tests/test_question_reviews.py -q`

Expected: FAIL because `questionReviews` is missing from the report response.

- [ ] **Step 3: Implement backend fallback and normalization**

In `backend_python/routes/interview.py`, add helper functions above `interview_report`:

```python
WEAK_ANSWER_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")
ALLOWED_ANSWER_STATUSES = {"完整", "模糊", "不会", "跑题"}


def classify_answer_status(answer_text: str) -> str:
    normalized = (answer_text or "").strip()
    if not normalized:
        return "不会"
    if any(marker in normalized for marker in WEAK_ANSWER_MARKERS):
        return "不会"
    if len(normalized) < 24:
        return "模糊"
    return "完整"


def normalize_string_list(value: Any, *, limit: int = 3, fallback: list[str] | None = None) -> list[str]:
    if not isinstance(value, list):
        return fallback or []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] or (fallback or [])


def fallback_question_review(answer: dict[str, Any], index: int) -> dict[str, Any]:
    focus = str(answer.get("focus") or answer.get("stage") or "综合能力").strip()
    question = str(answer.get("question") or "本题未记录问题文本").strip()
    answer_text = str(answer.get("answer") or "").strip()
    status = classify_answer_status(answer_text)
    return {
        "index": index,
        "focus": focus,
        "question": question,
        "answerStatus": status,
        "whyAsked": f"这道题用于确认你对「{focus}」的理解和表达是否扎实。",
        "missingPoints": ["概念解释", "项目例子", "验证方式"] if status != "完整" else ["量化结果", "技术取舍", "复盘总结"],
        "referenceDirection": "建议按背景、做法、原因、结果的顺序组织回答，并补充一个项目中的具体例子。",
        "trainingAction": f"围绕「{focus}」准备一段 1 分钟回答，至少包含一个项目细节和一个验证方式。",
    }


def normalize_question_review(review: Any, answer: dict[str, Any], index: int) -> dict[str, Any]:
    fallback = fallback_question_review(answer, index)
    if not isinstance(review, dict):
        return fallback
    status = str(review.get("answerStatus") or fallback["answerStatus"]).strip()
    if status not in ALLOWED_ANSWER_STATUSES:
        status = fallback["answerStatus"]
    return {
        "index": int(review.get("index") or index),
        "focus": str(review.get("focus") or fallback["focus"]).strip(),
        "question": str(review.get("question") or fallback["question"]).strip(),
        "answerStatus": status,
        "whyAsked": str(review.get("whyAsked") or fallback["whyAsked"]).strip(),
        "missingPoints": normalize_string_list(review.get("missingPoints"), fallback=fallback["missingPoints"]),
        "referenceDirection": str(review.get("referenceDirection") or fallback["referenceDirection"]).strip(),
        "trainingAction": str(review.get("trainingAction") or fallback["trainingAction"]).strip(),
    }


def build_question_reviews(result: dict[str, Any], answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model_reviews = result.get("questionReviews")
    reviews = model_reviews if isinstance(model_reviews, list) else []
    return [
        normalize_question_review(reviews[index] if index < len(reviews) else None, answer, index + 1)
        for index, answer in enumerate(answers)
    ]
```

Then change the return value of `interview_report`:

```python
    return {
        "score": int(result.get("score") or 60),
        "strengths": result.get("strengths") or [],
        "risks": result.get("risks") or [],
        "actions": result.get("actions") or [],
        "questionReviews": build_question_reviews(result, payload.answers),
    }
```

- [ ] **Step 4: Run backend tests to verify GREEN**

Run: `python -m pytest tests/test_question_reviews.py -q`

Expected: PASS.

## Task 2: Backend Prompt Contract

**Files:**
- Modify: `backend_python/prompts/interview.py`
- Test: `tests/test_question_reviews.py`

- [ ] **Step 1: Write failing prompt contract test**

Append to `tests/test_question_reviews.py`:

```python
def test_report_prompt_requests_question_reviews() -> None:
    from backend_python.prompts.interview import REPORT_SYSTEM_PROMPT

    assert "questionReviews" in REPORT_SYSTEM_PROMPT
    assert "answerStatus" in REPORT_SYSTEM_PROMPT
    assert "whyAsked" in REPORT_SYSTEM_PROMPT
    assert "trainingAction" in REPORT_SYSTEM_PROMPT
```

- [ ] **Step 2: Run prompt test to verify RED**

Run: `python -m pytest tests/test_question_reviews.py::test_report_prompt_requests_question_reviews -q`

Expected: FAIL because the current prompt only requests `score`, `strengths`, `risks`, and `actions`.

- [ ] **Step 3: Update report prompt**

Replace `REPORT_SYSTEM_PROMPT` in `backend_python/prompts/interview.py` with a UTF-8 Chinese prompt equivalent to:

```python
REPORT_SYSTEM_PROMPT = (
    "你是一个稳定、客观、严谨但偏学习辅导的面试复盘教练。只输出 JSON，不要输出 Markdown。"
    "JSON 格式必须是 {\"score\":数字,\"strengths\":[\"\"],\"risks\":[\"\"],\"actions\":[\"\"],"
    "\"questionReviews\":[{\"index\":1,\"focus\":\"\",\"question\":\"\",\"answerStatus\":\"完整|模糊|不会|跑题\","
    "\"whyAsked\":\"\",\"missingPoints\":[\"\"],\"referenceDirection\":\"\",\"trainingAction\":\"\"}]}。"
    "评分范围 0 到 100。strengths、risks、actions 各输出 3 条，每条不超过 45 个中文字符。"
    "questionReviews 必须和用户 answers 一一对应，index 从 1 开始。"
    "answerStatus 只能使用 完整、模糊、不会、跑题 四类。"
    "whyAsked 要解释为什么问这道题，可关联岗位、JD、简历、RAG 上下文或上一轮回答。"
    "missingPoints 最多 3 条，每条不超过 30 个中文字符。"
    "referenceDirection 不要写成长篇标准答案，而要给出下次如何组织回答。"
    "trainingAction 必须是一个可执行训练动作，不要写空泛鼓励。"
    "反馈要具体、可执行，语气偏学习辅导，不要羞辱用户。"
    "评分时必须参考岗位知识库 RAG 的评分点和风险信号、题库 RAG 的答题要点，也要参考候选人画像 RAG 的历史弱点。"
    "当前这一轮答案的表现优先于历史记录。"
)
```

- [ ] **Step 4: Run prompt test to verify GREEN**

Run: `python -m pytest tests/test_question_reviews.py::test_report_prompt_requests_question_reviews -q`

Expected: PASS.

## Task 3: Current Report Frontend Rendering

**Files:**
- Modify: `app.js`
- Test: `tests/frontend_interview_flow.test.mjs`

- [ ] **Step 1: Write failing frontend test for current report**

Append to `tests/frontend_interview_flow.test.mjs` inside the VM scenario or add a focused scenario after existing assertions:

```javascript
context.session.answers = [
  {
    stage: "技术追问",
    focus: "RAG 召回链路",
    question: "请解释 RAG 命中日志怎么设计？",
    answer: "不知道"
  }
];
context.renderReport({
  score: 52,
  strengths: ["能说出字段含义"],
  risks: ["缺少 JSON 示例"],
  actions: ["准备日志示例"],
  questionReviews: [
    {
      index: 1,
      focus: "RAG 召回链路",
      question: "请解释 RAG 命中日志怎么设计？",
      answerStatus: "不会",
      whyAsked: "用于确认你是否理解 RAG 可观测性。",
      missingPoints: ["字段结构", "质量评分"],
      referenceDirection: "按 query、retriever、hits、quality 说明。",
      trainingAction: "写一条合法 JSON 日志并解释字段。"
    }
  ]
});
context.__reportReviewHtml = context.reportContent.innerHTML;
```

Add assertions:

```javascript
assert.match(context.__reportReviewHtml, /逐题学习复盘/);
assert.match(context.__reportReviewHtml, /RAG 召回链路/);
assert.match(context.__reportReviewHtml, /用于确认你是否理解 RAG 可观测性/);
assert.match(context.__reportReviewHtml, /写一条合法 JSON 日志/);
```

- [ ] **Step 2: Run frontend test to verify RED**

Run: `node tests/frontend_interview_flow.test.mjs`

Expected: FAIL because `renderReport` does not render `questionReviews`.

- [ ] **Step 3: Implement shared frontend rendering helpers**

In `app.js`, add helpers near existing report helpers:

```javascript
function findAnswerForReview(review, index, answers = session.answers) {
  return answers[index] || answers.find((answer) => answer.question === review.question) || {};
}

function createQuestionReviewCards(questionReviews = [], answers = session.answers) {
  if (!Array.isArray(questionReviews) || questionReviews.length === 0) {
    return "";
  }

  const cards = questionReviews
    .map((review, index) => {
      const answer = findAnswerForReview(review, index, answers);
      const missingPoints = createList(review.missingPoints || []);
      return `
        <article class="question-review-card">
          <div class="question-review-heading">
            <div>
              <span class="eyebrow">第 ${review.index || index + 1} 题</span>
              <h3>${review.focus || answer.focus || "综合能力"}</h3>
            </div>
            <span class="status-badge">${review.answerStatus || "模糊"}</span>
          </div>
          <div class="review-detail">
            <strong>原问题</strong>
            <p>${review.question || answer.question || "本题未记录问题文本"}</p>
          </div>
          <div class="review-detail">
            <strong>我的回答</strong>
            <p>${answer.answer || "本题未作答"}</p>
          </div>
          <div class="review-detail">
            <strong>为什么问</strong>
            <p>${review.whyAsked || "用于确认当前考察点是否理解扎实。"}</p>
          </div>
          <div class="review-detail">
            <strong>缺失点</strong>
            ${missingPoints || "<p>建议补充概念解释、项目例子和验证方式。</p>"}
          </div>
          <div class="review-detail">
            <strong>参考回答方向</strong>
            <p>${review.referenceDirection || "建议按背景、做法、原因、结果的顺序组织回答。"}</p>
          </div>
          <div class="review-detail">
            <strong>下一步训练</strong>
            <p>${review.trainingAction || "围绕该考察点准备一段 1 分钟回答。"}</p>
          </div>
        </article>
      `;
    })
    .join("");

  return `
    <section class="question-review-section">
      <div class="section-heading compact">
        <span class="eyebrow">Learning Review</span>
        <h2>逐题学习复盘</h2>
      </div>
      <div class="question-review-list">${cards}</div>
    </section>
  `;
}
```

Update `renderReport(report)` to append:

```javascript
    ${createQuestionReviewCards(report.questionReviews || [], session.answers)}
```

- [ ] **Step 4: Add minimal styles**

In `styles.css`, add styles for:

```css
.question-review-section { margin-top: 24px; }
.question-review-list { display: grid; gap: 14px; }
.question-review-card { border: 1px solid var(--border); border-radius: 8px; padding: 16px; background: var(--surface); }
.question-review-heading { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.question-review-heading h3 { margin: 4px 0 0; font-size: 18px; }
.status-badge { border: 1px solid var(--border); border-radius: 999px; padding: 4px 10px; font-size: 12px; white-space: nowrap; }
.review-detail { margin-top: 12px; }
.review-detail strong { display: block; margin-bottom: 4px; font-size: 13px; color: var(--muted); }
.review-detail p { margin: 0; line-height: 1.7; }
```

- [ ] **Step 5: Run frontend test to verify GREEN**

Run: `node tests/frontend_interview_flow.test.mjs`

Expected: PASS.

## Task 4: History Review Frontend Rendering

**Files:**
- Modify: `app.js`
- Modify: `tests/frontend_history_review.test.mjs`

- [ ] **Step 1: Write failing history review test**

Update the fake history item in `tests/frontend_history_review.test.mjs` so `report` includes:

```javascript
questionReviews: [
  {
    index: 1,
    focus: "RAG 召回链路",
    question: "How does RAG work?",
    answerStatus: "模糊",
    whyAsked: "用于确认检索增强生成的基本链路。",
    missingPoints: ["召回", "生成"],
    referenceDirection: "先讲 retrieve，再讲 generate。",
    trainingAction: "画出 RAG 请求链路图。"
  }
]
```

Add assertions:

```javascript
assert.match(context.__result.reviewHtml, /逐题学习复盘/);
assert.match(context.__result.reviewHtml, /用于确认检索增强生成的基本链路/);
assert.match(context.__result.reviewHtml, /画出 RAG 请求链路图/);
```

- [ ] **Step 2: Run history frontend test to verify RED**

Run: `node tests/frontend_history_review.test.mjs`

Expected: FAIL because history review still renders only the old answer list.

- [ ] **Step 3: Render question reviews in history review**

In `showHistoryReview(item)`, replace or augment the answer-list block with:

```javascript
${createQuestionReviewCards(report.questionReviews || [], item.answers || []) || createAnswerReviewList(item.answers || [])}
```

If no `createAnswerReviewList` exists, extract the existing answer-list HTML into:

```javascript
function createAnswerReviewList(answers = []) {
  return `
    <div class="answer-review-list">
      ${answers
        .map(
          (answer, index) => `
            <article class="answer-review-item">
              <h3>${index + 1}. ${answer.focus || inferQuestionFocus(answer)}</h3>
              <p><strong>问题：</strong>${answer.question}</p>
              <p><strong>回答：</strong>${answer.answer || "未作答"}</p>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}
```

- [ ] **Step 4: Run history frontend test to verify GREEN**

Run: `node tests/frontend_history_review.test.mjs`

Expected: PASS.

## Task 5: Cache Bust and Full Verification

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Bump frontend script version**

In `index.html`, change the `app.js` query string to a new version:

```html
<script src="/app.js?v=20260605-question-review-coach"></script>
```

- [ ] **Step 2: Run focused verification**

Run:

```powershell
python -m pytest tests/test_question_reviews.py -q
node tests/frontend_interview_flow.test.mjs
node tests/frontend_history_review.test.mjs
node --check app.js
```

Expected: all pass.

- [ ] **Step 3: Run broader regression verification**

Run:

```powershell
python -m pytest -q
node tests/frontend_rag_quality.test.mjs
node tests/frontend_rag_logs.test.mjs
node tests/frontend_rag_documents.test.mjs
node tests/frontend_auth_refresh.test.mjs
```

Expected: all pass.

- [ ] **Step 4: Browser smoke test**

Open `http://localhost:8000/` in the in-app browser, reload, and verify:

- The loaded script URL includes `20260605-question-review-coach`.
- Generating or viewing a report shows “逐题学习复盘”.
- Existing history review still opens.

## Self-Review

- Spec coverage: The plan covers backend report structure, fallback behavior, prompt contract, current report rendering, history rendering, old data fallback, tests, and browser verification.
- Placeholder scan: No TBD/TODO placeholders are left in implementation steps.
- Type consistency: The same field names are used across backend, frontend, tests, and the design spec: `questionReviews`, `answerStatus`, `whyAsked`, `missingPoints`, `referenceDirection`, `trainingAction`.
