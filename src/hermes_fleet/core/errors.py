"""RFC 7807 problem details and the service's error hierarchy."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_CT = "application/problem+json"


class FleetError(Exception):
    """Base error: carries an HTTP status and a stable machine code."""

    status: int = 500
    code: str = "internal_error"
    title: str = "Internal error"

    def __init__(self, detail: str = "", *, extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        self.extra = extra or {}


class NotFound(FleetError):
    status, code, title = 404, "not_found", "Not found"


class Conflict(FleetError):
    status, code, title = 409, "conflict", "Conflict"


class BadRequest(FleetError):
    status, code, title = 400, "bad_request", "Bad request"


class Unprocessable(FleetError):
    status, code, title = 422, "unprocessable", "Unprocessable entity"


class Unauthorized(FleetError):
    status, code, title = 401, "unauthorized", "Unauthorized"


class Forbidden(FleetError):
    status, code, title = 403, "forbidden", "Forbidden"


class UpstreamUnavailable(FleetError):
    status, code, title = 503, "upstream_unavailable", "Upstream unavailable"


class UpstreamError(FleetError):
    status, code, title = 502, "upstream_error", "Upstream error"


def problem(
    status: int, title: str, detail: str, code: str, instance: str, **extra: Any
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://hermes-fleet.local/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "instance": instance,
    }
    body.update(extra)
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(body, status_code=status, media_type=PROBLEM_CT, headers=headers)


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(FleetError)
    async def _fleet(request: Request, exc: FleetError) -> JSONResponse:
        return problem(exc.status, exc.title, exc.detail, exc.code, request.url.path, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized"}.get(
            exc.status_code, "http_error"
        )
        return problem(exc.status_code, str(exc.detail), str(exc.detail), code, request.url.path)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return problem(
            422,
            "Validation failed",
            "request did not match the schema",
            "validation_error",
            request.url.path,
            errors=errors,
        )
