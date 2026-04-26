"""Rate limiter wired into the FastAPI app.

slowapi binds each ``@limiter.limit(...)`` decorator to the specific
``Limiter`` instance that owns it, so the limiter has to live at module
scope (not be rebuilt per-app). Tests that need a clean counter call
``limiter.reset()``.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limiter using slowapi's default in-memory storage. The decorators
# in routers/auth.py bind to this exact instance.
limiter = Limiter(key_func=get_remote_address)
