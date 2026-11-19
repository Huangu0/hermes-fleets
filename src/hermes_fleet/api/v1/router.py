from __future__ import annotations

from fastapi import APIRouter

from hermes_fleet.api.v1 import audit

api_router = APIRouter(prefix="/v1")
api_router.include_router(audit.router)
