# denchik

Trello/Jira/Asana-style task tracker that exposes the **same** task tree two
ways: a kanban board and a forum. Built on FastAPI + SQLAlchemy 2 (async,
aiosqlite) + Python 3.12 on the backend, React 18 + Vite 6 + TypeScript 5 +
TanStack Query 5 + Zustand 5 + MSW 2 on the frontend. Storage: SQLite
(`./data/denchik.db`). Auth: JWT in `denchik_session` httpOnly cookie. The
whole stack runs in Docker — there is no expectation that any tooling is
installed on the host.

## Workflow rules

These come from explicit user feedback, not from convention — break them and
the user has to re-correct. They are short on purpose.

- **Docker only, never modify the host.** Every dev/test/build action goes
  through `make ...` or `docker compose run --rm ...`. Don't `apt install`,
  `pip install`, `npm install`, or run Python/Node directly. If a one-off tool
  is needed (Playwright is the canonical case), spin a throwaway container
  with `--network=host` instead of installing it locally. The user has
  already corrected this once ("Настрой сперва докер, не нужно модифицировать
  хост-систему").
- **TDD for behaviour changes.** New endpoints, schema changes, or business
  rules (RBAC, nesting limits, position math, new component logic) get a
  failing pytest/vitest test first, then code. Cosmetic UI tweaks, log
  additions, and one-off scripts (e.g. `smoke.mjs`) are exempt.
- **Don't `git commit` unless asked.** Don't push without permission. The
  remote is a personal `origin/main` — there is no PR review pipeline.
- **English-grammar coaching.** When the user writes in English, fix his
  grammar errors and show the correction before acting. He is intentionally
  practising. Russian messages don't need this treatment; reply in Russian.

## Layout

```
backend/app/
  core/         settings, async db engine + session factory, security
                (bcrypt direct, NOT passlib), deps (current_user + RBAC)
  models/       SQLAlchemy ORM: User, Workspace + WorkspaceMember (M2M),
                EpicGroup, Epic, Task, Comment (self-referential parent_id),
                Label + TaskLabel (M2M), Attachment
  schemas/      Pydantic v2 request/response
  routers/      auth, workspaces, epic_groups, epics, tasks, comments,
                labels, attachments, forum (read-only aggregate)
  services/     position helpers
  main.py       FastAPI factory; lifespan auto-creates schema via
                Base.metadata.create_all (Alembic is wired but unused)
backend/tests/  pytest + httpx ASGITransport (27 tests at last green run)
frontend/src/
  api/          fetch wrapper (`credentials: include`) + typed endpoint
                helpers; BASE = VITE_API_URL ?? "/api"
  hooks/        TanStack Query hooks (useAuth, useEpics, useTasks, ...)
  store/        Zustand auth store
  components/   BoardView (HTML5 drag-and-drop), ForumView, QuickAddTask,
                TaskDetail
  pages/        AuthPage, WorkspacePage, TaskPage
  test/         MSW server + render utils (10 tests at last green run)
data/           Mounted into backend container at /app/data — survives
                `make down`. SQLite DB + ./attachments/.
```

## Commands (always inside containers)

- `make up` / `make down` — full stack on `:8000` (api) + `:5173` (web)
- `make logs` — tail both containers
- `make test` — backend + frontend
- `make test-backend` / `make test-frontend` — single suite
- `make backend-shell` / `make frontend-shell` — bash inside the container
- `make clean` — remove volumes, images, db, attachments

There is **no `make restart`**. Use `make down && make up` (full rebuild) or
`docker compose restart <svc>` (no rebuild — won't pick up Dockerfile
changes, but is fine for `--reload` source changes).

## Conventions worth knowing

These are project-specific gotchas that you cannot derive from reading the
code — they exist *because* of past failures or external library quirks.

### Backend

- **Async SQLAlchemy + M2M.** Never assign through a relationship attribute
  in async code (`task.labels = [...]`). The lazy-load needed to flush such
  assignment fires synchronously and raises `MissingGreenlet`. Manage M2M
  rows by hand: `delete(TaskLabel).where(...)` then
  `insert(TaskLabel), [{...}, ...]`. The canonical pattern is in
  `backend/app/routers/tasks.py::_attach_labels`. Apply the same shape to
  any future M2M (workspace members, future tag systems, etc.).
- **bcrypt is used directly.** `passlib[bcrypt]` was removed because the
  bcrypt 4.x release broke the `__about__` introspection that passlib does
  on import (`AttributeError: module 'bcrypt' has no attribute '__about__'`).
  We hash with `bcrypt.hashpw(pw[:72], bcrypt.gensalt())` in
  `core/security.py` and **truncate the password to 72 bytes by hand** —
  bcrypt rejects longer inputs since 4.x. Do not reintroduce passlib.
- **Comment nesting is enforced in the router, not the DB.** A reply to a
  reply returns 400 from `routers/comments.py`. The DB column
  `comment.parent_comment_id` is a plain self-FK with no DB-level depth
  check. If you add a new write path for comments, re-implement the check
  there too, otherwise users will end up with 3-level threads in storage.
- **Test isolation.** `backend/tests/conftest.py` builds a fresh tempdir
  SQLite per session and resets the engine via `reset_engine_for_tests()`.
  When verifying 401 paths with httpx, remember that `client` and
  `auth_client` share a cookie jar — call `client.cookies.clear()` before
  asserting unauthenticated behaviour or you will get a false 201/200.
- **Request-logging middleware** in `main.py` is intentionally chatty
  (logs method/path/cookies/body/status/timing). Keep it for now — the
  user explicitly asked for verbose logs while debugging the workspace
  flow. Trim only when he asks.

### Frontend

- **`api` BASE.** `frontend/src/api/client.ts` reads
  `import.meta.env.VITE_API_URL ?? "/api"`. Compose sets it to
  `http://localhost:8000`, so MSW handlers in `src/test/msw-server.ts`
  must use a wildcard host (`http.get("*/path", ...)`) — otherwise tests
  pass locally and break in CI when env vars differ.
- **Quick-create UX is sacred.** `POST /tasks` accepts only
  `epic_id + title`. `QuickAddTask` is a single click → input → Enter →
  refocus loop. Don't add required fields to the create form, don't
  introduce a modal, don't validate beyond `title.trim() !== ""`. Every
  Trello/Jira escape hatch the user wanted to avoid lives in
  `TaskDetail` after creation.
- **IME composition swallows Enter.** When a Russian/Chinese/Japanese
  IME is active, the Enter that finishes composition is consumed by the
  IME and **does not fire `keydown` with `key === "Enter"`** in React's
  synthetic event. So any input that submits on Enter must also expose
  a button or a form-level submit. `NewItemInput` in
  `pages/WorkspacePage.tsx` does both — copy that pattern for new
  inline-add inputs.
- **Drag-and-drop in tests.** jsdom does not propagate the `dataTransfer`
  payload through `dispatchEvent(new DragEvent(...))`. Use
  `fireEvent.dragStart(card, { dataTransfer })` /
  `fireEvent.drop(target, { dataTransfer })` from
  `@testing-library/react` with a hand-rolled `dataTransfer` object — see
  `BoardView.test.tsx` for the working shape.

### Data & infra

- **Forum view has no table.** `GET /forum/{epic_group_id}` is a read-only
  aggregate built on the fly: epic_group → epics → tasks with comment
  count and last-comment metadata per task. If you change the comment or
  task model, update the aggregate query in `routers/forum.py` to match —
  there is no schema to keep in sync, only this query.
- **`./data/denchik.db` is mounted.** `make down` does NOT wipe state.
  Use `make clean` for a real reset (drops volumes + images and removes
  `data/*.db` + attachments).
- **Vite dev server rejects non-localhost Host headers with 403.** This
  matters when driving the frontend from a Playwright container: use
  `--network=host` and `http://localhost:5173`, not
  `http://host.docker.internal:5173`. The headless smoke harness lives at
  `./smoke.mjs` (gitignored) — see the assistant's memory entry
  `reference_smoke_harness.md` for the full `docker run` invocation.
