from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.db.connection import get_db
from backend.schemas.dashboard import DashboardMeResponse
from backend.services.dashboard_service import get_dashboard_me

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me", response_model=DashboardMeResponse)
def dashboard_me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> DashboardMeResponse:
    return get_dashboard_me(
        conn,
        current_user=current_user,
    )