from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.db.connection import get_db
from backend.schemas.preferences import PreferencesResponse
from backend.services.preferences_service import get_preferences

router = APIRouter(tags=["preferences"])


@router.get(
    "/preferences",
    response_model=PreferencesResponse,
)
def preferences(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
) -> PreferencesResponse:

    payload = get_preferences(
        conn,
        tenant_id=current_user["tenant_id"],
    )

    return PreferencesResponse(**payload)