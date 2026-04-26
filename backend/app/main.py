import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.db import Base, get_engine
from app.core.rate_limit import limiter
from app.routers import (
    attachments,
    auth,
    comments,
    epic_groups,
    epics,
    forum,
    labels,
    tasks,
    workspaces,
)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("denchik")

SENSITIVE_PATHS = {"/auth/login", "/auth/register"}
SENSITIVE_FIELDS = {"password", "current_password", "new_password"}


def _redact_body_for_log(path: str, body: bytes) -> str:
    if not body:
        return ""
    if path in SENSITIVE_PATHS:
        try:
            parsed = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return "<unparseable redacted body>"
        if isinstance(parsed, dict):
            for key in list(parsed.keys()):
                if key in SENSITIVE_FIELDS:
                    parsed[key] = "<redacted>"
        return json.dumps(parsed)
    return body[:500].decode("utf-8", "replace")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = b""
        if request.method in {"POST", "PATCH", "PUT"}:
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(request.scope, receive)
        log.info(
            "→ %s %s qs=%s cookies=%s body=%s",
            request.method,
            request.url.path,
            dict(request.query_params),
            {k: ("<set>" if v else "<empty>") for k, v in request.cookies.items()},
            _redact_body_for_log(request.url.path, body),
        )
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("✗ %s %s raised", request.method, request.url.path)
            raise
        dt_ms = (time.perf_counter() - t0) * 1000
        log.info("← %s %s %d in %.1fms", request.method, request.url.path, response.status_code, dt_ms)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="denchik", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(epic_groups.router)
    app.include_router(epics.router)
    app.include_router(tasks.router)
    app.include_router(comments.router)
    app.include_router(labels.router)
    app.include_router(attachments.router)
    app.include_router(forum.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
