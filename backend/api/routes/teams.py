from typing import Any, Annotated
from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PGConnection

from backend.api.deps import get_current_user
from backend.db.connection import get_db
from backend.services.team_service import get_my_team_overview

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/me")
def get_my_team(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PGConnection, Depends(get_db)],
):
    return get_my_team_overview(
        conn,
        current_user=current_user,
    )