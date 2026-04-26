# denchik

A Trello / Jira / Asana-style task system with a built-in **forum view**:
the same task tree can be viewed as a kanban board *or* as a forum where
epic groups are forums, epics are subforums, tasks are topics, and
comments are messages (one level of nesting).

Runs entirely in Docker: Python 3.12 + FastAPI + SQLite on the backend,
React 18 + Vite + TanStack Query on the frontend.

## Quick start

```bash
make up         # build & start backend (:8000) and frontend (:5173)
open http://localhost:5173
```

Stop:

```bash
make down
```

## Running tests

```bash
make test            # backend pytest + frontend vitest
make test-backend    # 27 tests
make test-frontend   # 10 tests
```

Both suites run inside their respective containers — no host installs needed.

## Layout

```
backend/                  FastAPI app
  app/
    core/                 config, db engine, security, deps
    models/               SQLAlchemy ORM
    schemas/              Pydantic request/response models
    services/             business helpers (positions, etc.)
    routers/              HTTP endpoints
    main.py               FastAPI factory
  tests/                  pytest (httpx + ASGITransport)
  alembic/                migrations (auto-create_all is also enabled in lifespan)
frontend/                 React + Vite + TS
  src/
    api/                  typed client + endpoint helpers
    hooks/                TanStack Query hooks
    store/                Zustand stores
    components/           BoardView, ForumView, QuickAddTask, TaskDetail
    pages/                AuthPage, WorkspacePage, TaskPage
    test/                 MSW server, test utilities
docker-compose.yml
Makefile
```

## Concepts

| Forum vocabulary  | App entity      |
|-------------------|-----------------|
| Forum             | EpicGroup       |
| Subforum          | Epic            |
| Topic             | Task            |
| Message           | Comment         |
| Reply (1 level)   | Reply Comment   |

A workspace owns many epic groups; an epic group owns many epics; an
epic owns many tasks; a task owns many comments. Comments support
exactly one level of nesting (a reply, no reply-to-reply).

## Minimum-action task creation

`POST /tasks` accepts only `epic_id` + `title`. Status defaults to
`todo`, priority to `med`, position is appended. The board UI
exposes this as a one-input "+ Add task" affordance per column —
type the title, press Enter, the input stays focused for the next one.

## API surface

```
POST   /auth/register     POST /auth/login       POST /auth/logout
GET    /auth/me

GET    /workspaces        POST /workspaces
POST   /workspaces/{id}/members

GET    /epic-groups?workspace_id=
POST   /epic-groups       DELETE /epic-groups/{id}

GET    /epics?epic_group_id=
POST   /epics             PATCH /epics/{id}      DELETE /epics/{id}

GET    /tasks?epic_id=
POST   /tasks             GET /tasks/{id}        PATCH /tasks/{id}
DELETE /tasks/{id}

GET    /tasks/{id}/comments       POST /tasks/{id}/comments
PATCH  /tasks/{id}/comments/{cid} DELETE /tasks/{id}/comments/{cid}

GET    /labels?workspace_id=      POST /labels

GET    /tasks/{id}/attachments    POST /tasks/{id}/attachments  (multipart)
GET    /attachments/{id}/download

GET    /forum/{epic_group_id}     # nested view: subforums → topics → counts
```

Auth is JWT in an httpOnly cookie (`denchik_session`). All non-auth
endpoints require workspace membership.

## Where the SQLite file lives

`./data/denchik.db` (mounted into the backend container at
`/app/data/denchik.db`). Attachments live next to it under
`./data/attachments/`.

## Development tips

- The backend uses `Base.metadata.create_all` in lifespan, so the
  schema is provisioned automatically on first boot. Alembic is wired
  up if you prefer migrations:
  `docker compose run --rm backend alembic revision --autogenerate -m "msg"`.
- Frontend hot-reloads via Vite. Backend reloads on save via uvicorn
  `--reload`.
- `make backend-shell` / `make frontend-shell` drop you into a container.
