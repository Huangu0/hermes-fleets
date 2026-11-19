"""Static Bearer API-key authentication."""

from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hermes_fleet.core.errors import Unauthorized

_bearer = HTTPBearer(auto_error=False)


async def require_api_key(request: Request) -> str:
    creds: HTTPAuthorizationCredentials | None = await _bearer(request)
    expected: str = request.app.state.api_key
    if creds is None or creds.scheme.lower() != "bearer":
        raise Unauthorized("missing bearer API key")
    if not hmac.compare_digest(creds.credentials.encode(), expected.encode()):
        raise Unauthorized("invalid API key")
    # The actor recorded in audit entries; a single static key maps to one actor.
    actor = request.headers.get("X-Fleet-Actor", "api-key")
    request.state.actor = actor[:64]
    return str(request.state.actor)
