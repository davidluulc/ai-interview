# Frontend Redesign Baseline

Pre-redesign baseline for the neo-brutalism frontend redesign
(plan: `frontend-neobrutalism-redesign.md`). Later tasks must not regress
these numbers.

- **Date:** 2026-09-16
- **Branch:** `frontend-neobrutalism-redesign`
- **Base commit:** b1312d3 (`docs: fix shadow-6 token in redesign plan`)

## Test baseline (Step 1)

Command: `cd frontend && npx vitest run`

- **Tests: 167 passed / 167 total** (31 test files, 31 passed / 31 total)
- Duration: 4.04s

## Build baseline (Step 2)

Command: `cd frontend && npm run build` (`vue-tsc --noEmit && vite build`)

- **Build: GREEN** — exit code 0, `✓ built in 1.76s`
- Type-check (`vue-tsc --noEmit`) passed with the build

## Notes

- `frontend/node_modules` was missing on this machine; restored with
  `npm ci` before recording (no dependency or lockfile changes).
- Regression bar for redesign tasks: tests must stay 167/167 passing and
  `npm run build` must stay green (exit 0).
