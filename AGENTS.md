# Repository Guidelines

## Project Structure & Module Organization
This repo is split into `backend/`, `frontend/`, and `e2e/`.
- `backend/app/`: FastAPI app code (`routers/`, `services/`, `models.py`, `database.py`, `main.py`).
- `backend/tests/`: API, scraper, and normalization tests with shared fixtures.
- `frontend/src/`: React + TypeScript UI (`components/`, `api/`, `utils/`, `test/`).
- `e2e/`: Playwright-based end-to-end tests run with `pytest`.
- Root `test_*.py` scripts are scenario/regression utilities that also write artifacts to `test_screenshots/`.

## Build, Test, and Development Commands
- `./run.sh setup`: Install backend/frontend dependencies.
- `./run.sh`: Start backend (`:8000`) and frontend (`:5173`) together.
- `./run.sh backend` / `./run.sh frontend`: Start one service only.
- `cd backend && uv sync --group dev`: Install/sync backend dependencies.
- `cd backend && uv run pytest`: Run backend tests.
- `cd backend && uv run ruff check . && uv run ruff format .`: Lint and format backend code.
- `cd backend && uv run ty check`: Run backend static type checks.
- `cd frontend && npm run dev`: Start frontend dev server.
- `cd frontend && npm run build && npm run lint && npm run test:run`: Validate frontend build, lint, and tests.
- `cd e2e && pytest`: Run Playwright E2E tests (requires services running via `./run.sh`).

## Coding Style & Naming Conventions
Use idiomatic, strongly typed code and keep modules focused.
- Python: PEP 8, type hints, docstrings for modules/public functions, `snake_case` names, `PascalCase` classes.
- Python tooling: use `uv` for dependency management, `ruff` for linting/formatting, and `ty` for type checking.
- TypeScript: keep `strict`-safe code (avoid `any`), `PascalCase` components, `useX` hooks, and `*.test.tsx` for component tests.
- Keep API client code in `frontend/src/api/`; keep backend business logic in `backend/app/services/`.

## Testing Guidelines
Add or update tests with each behavior change.
- Backend: `pytest` + FastAPI `TestClient`, files named `test_*.py` under `backend/tests/`.
- Frontend: Vitest + Testing Library, colocated tests such as `frontend/src/components/GroceryList.test.tsx`.
- E2E: `pytest-playwright` tests under `e2e/`, covering multi-tab user flows.

## Commit & Pull Request Guidelines
Git history is currently minimal, so use a clear standard going forward.
- Commits: short imperative subject with scope when useful (example: `frontend: fix grocery sort reset`).
- Keep commits focused and reviewable; avoid mixing refactors with behavior changes.
- PRs should include: summary, linked issue/task, test commands run, and screenshots for UI changes.

## Security & Configuration Tips
Configuration is environment-driven.
- Use `.env` for `DATABASE_URL` and `OPENAI_API_KEY` (read by backend services).
- Do not commit secrets or local database artifacts.
