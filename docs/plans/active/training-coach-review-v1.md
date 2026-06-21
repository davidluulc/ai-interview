# Training Coach Review V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the training page from self-rating/check-in into a useful coach review flow that gives a reference answer, concrete corrections, and a rewritten answer.

**Architecture:** Keep the current `TrainingTask` table and `/complete` endpoint. Replace self-rated mastery UI with a submit-once coach review payload stored under `metadata.lastPractice.review`; generate the first version by deterministic template/rubric logic so it is stable and token-free, with room for LLM review later.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Vue3, Pinia, Vitest.

---

## File Map

- `backend_python/training_tasks.py`: build coach review payload from template key points and answer text; stop mastery from being the primary product signal.
- `tests/test_training_practice_route.py`: verify `/complete` returns reference answer, issues, rewrite, next practice, and duplicate protection.
- `frontend/src/api/training.ts`: add `TrainingPracticeReview` type.
- `frontend/src/stores/training.ts`: keep submit-once guard; expose review through last result metadata.
- `frontend/src/components/training/TrainingPracticePanel.vue`: remove answer-status/self-rating controls from the primary UI; show coach review cards.
- `frontend/src/components/training/TrainingPracticePanel.test.ts`: verify review display and no self-rating controls.
- `frontend/src/pages/app/TrainingPage.vue` and test fixture: adapt props.

## Tasks

- [ ] Backend RED: add route test expecting `metadata.lastPractice.review.referenceAnswer`, `issues`, `rewrittenAnswer`, `nextPractice`, and no repeat scoring on duplicate submission.
- [ ] Backend GREEN: implement deterministic coach review generation from template answer key points, common mistakes, one-minute template, and user answer.
- [ ] Frontend RED: component test expects no `回答状态`/`自评分`, submit button says `提交给 AI 批改`, and review cards render `参考答案`、`需要纠正`、`建议改写`、`下一步练习`.
- [ ] Frontend GREEN: update types, store, page props, and practice panel UI.
- [ ] Verify: backend training tests, frontend training tests, frontend full tests, frontend build, backend full pytest.

## Scope Guard

This V1 does not add a new table, does not add streaming, and does not require model tokens. If we later want true LLM grading, it should plug into the same review shape.
