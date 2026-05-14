"""user_repository.py Repository helpers for schema-native tenant, user, and Graph identity access."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor
from psycopg2.extensions import connection as PGConnection

USER_SELECT_FIELDS = """
    au.id::text AS user_id,
    au.tenant_id::text AS tenant_id,
    au.external_user_id,
    au.email,
    au.full_name,
    au.display_name,
    au.mobile_phone,
    au.office_location,
    au.department,
    au.job_title,
    au.company_name,
    au.employee_id,
    au.microsoft_object_id,
    au.user_principal_name,
    au.manager_user_id::text AS manager_user_id,
    au.role_name AS role,
    au.status,
    au.home_site_id::text AS home_site_id,
    au.graph_last_synced_at,
    au.created_at,
    au.updated_at
"""

USER_SELECT_FROM = """
    FROM app_users AS au
"""

USER_RETURNING_FIELDS = """
    id::text AS user_id,
    tenant_id::text AS tenant_id,
    external_user_id,
    email,
    full_name,
    display_name,
    mobile_phone,
    office_location,
    department,
    job_title,
    company_name,
    employee_id,
    microsoft_object_id,
    user_principal_name,
    manager_user_id::text AS manager_user_id,
    role_name AS role,
    status,
    home_site_id::text AS home_site_id,
    graph_last_synced_at,
    created_at,
    updated_at
"""

ROLE_NAMES = {"EMPLOYEE", "OFFICE_ADMIN", "TENANT_ADMIN", "SUPPORT_ADMIN"}
USER_STATUSES = {"ACTIVE", "INACTIVE", "LOCKED"}


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_text(value: str | None, *, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if max_length is not None and len(normalized) > max_length:
        raise ValueError(f"Value exceeds schema limit of {max_length} characters.")
    return normalized


def _required_text(value: str | None, *, field_name: str, max_length: int) -> str:
    normalized = _normalize_text(value, max_length=max_length)
    if normalized is None:
        raise ValueError(f"{field_name} is required.")
    return normalized


def fetch_default_tenant_id(conn: PGConnection) -> str:
    """Resolve one active tenant when request-level tenant scoping is absent."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text
            FROM tenants
            WHERE status = 'ACTIVE'
            """
        )
        rows = cur.fetchall()

    if not rows:
        raise LookupError("No active tenant found.")
    if len(rows) > 1:
        raise LookupError(
            "Multiple active tenants exist; tenant cannot be resolved without an azure_tenant_id."
        )
    return rows[0][0]


def fetch_tenant_by_azure_tenant_id(conn: PGConnection, azure_tenant_id: str) -> dict[str, Any] | None:
    """Fetch the active application tenant whose tenant_key maps to Azure tid."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id::text AS tenant_id,
                tenant_key,
                tenant_name,
                status,
                created_at,
                updated_at
            FROM tenants
            WHERE tenant_key = %s
              AND status = 'ACTIVE'
            """,
            (azure_tenant_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def fetch_active_tenant_for_login(conn: PGConnection, *, azure_tenant_id: str) -> dict[str, Any] | None:
    """Resolve the tenant for SSO using tenant_key, falling back only if unambiguous."""
    tenant = fetch_tenant_by_azure_tenant_id(conn, azure_tenant_id)
    if tenant is not None:
        return tenant

    tenant_id = fetch_default_tenant_id(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id::text AS tenant_id,
                tenant_key,
                tenant_name,
                status,
                created_at,
                updated_at
            FROM tenants
            WHERE id = %s
              AND status = 'ACTIVE'
            """,
            (tenant_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def fetch_user_by_email(
    conn: PGConnection,
    email: str,
    *,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Fetch one user record by email address within a tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            {USER_SELECT_FROM}
            WHERE au.tenant_id = %s
              AND au.email = %s
            """,
            (tenant_id, _normalize_email(email)),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def fetch_user_by_id(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Fetch one tenant-scoped user record by app_users.id."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            {USER_SELECT_FROM}
            WHERE au.tenant_id = %s
              AND au.id = %s
            """,
            (tenant_id, user_id),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def fetch_user_by_microsoft_object_id(
    conn: PGConnection,
    *,
    tenant_id: str,
    microsoft_object_id: str,
) -> dict[str, Any] | None:
    """Fetch one user by the schema's Microsoft object id unique key."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            {USER_SELECT_FROM}
            WHERE au.tenant_id = %s
              AND au.microsoft_object_id = %s
            """,
            (tenant_id, _required_text(microsoft_object_id, field_name="microsoft_object_id", max_length=150)),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def fetch_user_by_sso_identity(
    conn: PGConnection,
    *,
    tenant_id: str,
    provider: str,
    provider_user_id: str,
) -> dict[str, Any] | None:
    """Fetch one user through auth_identities within the resolved tenant."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {USER_SELECT_FIELDS}
            FROM auth_identities AS ai
            INNER JOIN app_users AS au
                ON au.tenant_id = ai.tenant_id
               AND au.id = ai.user_id
            WHERE ai.tenant_id = %s
              AND ai.provider = %s
              AND ai.provider_user_id = %s
            """,
            (
                tenant_id,
                _required_text(provider, field_name="provider", max_length=50),
                _required_text(provider_user_id, field_name="provider_user_id", max_length=150),
            ),
        )
        result = cur.fetchone()
    return dict(result) if result else None


def create_app_user_from_graph(
    conn: PGConnection,
    *,
    tenant_id: str,
    microsoft_object_id: str,
    email: str,
    full_name: str,
    user_principal_name: str | None,
    display_name: str | None,
    mobile_phone: str | None,
    office_location: str | None,
    job_title: str | None,
    department: str | None,
    company_name: str | None,
    employee_id: str | None,
    manager_user_id: str | None,
) -> dict[str, Any]:
    """Create a first-time SSO user in app_users using schema-valid fields."""
    normalized_email = _required_text(_normalize_email(email), field_name="email", max_length=200)
    normalized_role = "EMPLOYEE"
    normalized_status = "ACTIVE"

    if normalized_role not in ROLE_NAMES:
        raise ValueError("Default role_name is not allowed by chk_app_users_role.")
    if normalized_status not in USER_STATUSES:
        raise ValueError("Default status is not allowed by chk_app_users_status.")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            INSERT INTO app_users (
                tenant_id,
                email,
                full_name,
                role_name,
                status,
                microsoft_object_id,
                user_principal_name,
                display_name,
                mobile_phone,
                office_location,
                job_title,
                department,
                company_name,
                employee_id,
                manager_user_id,
                graph_last_synced_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (tenant_id, microsoft_object_id) DO NOTHING
            RETURNING {USER_RETURNING_FIELDS}
            """,
            (
                tenant_id,
                normalized_email,
                _required_text(full_name, field_name="full_name", max_length=200),
                normalized_role,
                normalized_status,
                _required_text(microsoft_object_id, field_name="microsoft_object_id", max_length=150),
                _normalize_text(user_principal_name, max_length=200),
                _normalize_text(display_name, max_length=200),
                _normalize_text(mobile_phone, max_length=50),
                _normalize_text(office_location, max_length=200),
                _normalize_text(job_title, max_length=150),
                _normalize_text(department, max_length=150),
                _normalize_text(company_name, max_length=200),
                _normalize_text(employee_id, max_length=100),
                manager_user_id,
            ),
        )
        result = cur.fetchone()

    if result:
        return dict(result)

    existing = fetch_user_by_microsoft_object_id(
        conn,
        tenant_id=tenant_id,
        microsoft_object_id=microsoft_object_id,
    )
    if existing is None:
        raise LookupError("Unable to create or resolve the Microsoft SSO user.")
    return existing


def create_auth_identity_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
    provider: str,
    provider_tenant_id: str | None,
    provider_user_id: str,
    email: str,
    raw_profile: dict[str, Any],
) -> None:
    """Insert the provider identity row for a first-time SSO user."""
    normalized_provider = _required_text(provider, field_name="provider", max_length=50)
    normalized_provider_user_id = _required_text(provider_user_id, field_name="provider_user_id", max_length=150)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO auth_identities (
                tenant_id,
                user_id,
                provider,
                provider_tenant_id,
                provider_user_id,
                email,
                raw_profile
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider, provider_user_id) DO NOTHING
            """,
            (
                tenant_id,
                user_id,
                normalized_provider,
                _normalize_text(provider_tenant_id, max_length=100),
                normalized_provider_user_id,
                _required_text(_normalize_email(email), field_name="email", max_length=200),
                Json(raw_profile),
            ),
        )
        if cur.rowcount:
            return

        cur.execute(
            """
            SELECT tenant_id::text, user_id::text
            FROM auth_identities
            WHERE provider = %s
              AND provider_user_id = %s
            """,
            (normalized_provider, normalized_provider_user_id),
        )
        row = cur.fetchone()
    if row is None or str(row[0]) != str(tenant_id) or str(row[1]) != str(user_id):
        raise LookupError("Microsoft provider identity is already linked to a different user.")


def upsert_user_graph_profile(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
    graph_profile: dict[str, Any],
    manager_graph_object_id: str | None,
) -> None:
    """Store the enriched Microsoft Graph profile for a first-time SSO user."""
    graph_object_id = _required_text(str(graph_profile.get("id") or ""), field_name="graph_object_id", max_length=150)
    business_phones = graph_profile.get("businessPhones")
    if business_phones is not None and not isinstance(business_phones, list):
        raise ValueError("businessPhones must be a JSON array when present.")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_graph_profiles (
                tenant_id,
                user_id,
                graph_object_id,
                user_principal_name,
                display_name,
                given_name,
                surname,
                mail,
                mobile_phone,
                business_phones,
                job_title,
                department,
                company_name,
                employee_id,
                office_location,
                city,
                state,
                country,
                manager_graph_object_id,
                raw_profile,
                synced_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (tenant_id, user_id) DO UPDATE
            SET graph_object_id = EXCLUDED.graph_object_id,
                user_principal_name = EXCLUDED.user_principal_name,
                display_name = EXCLUDED.display_name,
                given_name = EXCLUDED.given_name,
                surname = EXCLUDED.surname,
                mail = EXCLUDED.mail,
                mobile_phone = EXCLUDED.mobile_phone,
                business_phones = EXCLUDED.business_phones,
                job_title = EXCLUDED.job_title,
                department = EXCLUDED.department,
                company_name = EXCLUDED.company_name,
                employee_id = EXCLUDED.employee_id,
                office_location = EXCLUDED.office_location,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                country = EXCLUDED.country,
                manager_graph_object_id = EXCLUDED.manager_graph_object_id,
                raw_profile = EXCLUDED.raw_profile,
                synced_at = NOW(),
                updated_at = NOW()
            """,
            (
                tenant_id,
                user_id,
                graph_object_id,
                _normalize_text(graph_profile.get("userPrincipalName"), max_length=200),
                _normalize_text(graph_profile.get("displayName"), max_length=200),
                _normalize_text(graph_profile.get("givenName"), max_length=100),
                _normalize_text(graph_profile.get("surname"), max_length=100),
                _normalize_text(graph_profile.get("mail"), max_length=200),
                _normalize_text(graph_profile.get("mobilePhone"), max_length=50),
                Json(business_phones) if business_phones is not None else None,
                _normalize_text(graph_profile.get("jobTitle"), max_length=150),
                _normalize_text(graph_profile.get("department"), max_length=150),
                _normalize_text(graph_profile.get("companyName"), max_length=200),
                _normalize_text(graph_profile.get("employeeId"), max_length=100),
                _normalize_text(graph_profile.get("officeLocation"), max_length=200),
                _normalize_text(graph_profile.get("city"), max_length=100),
                _normalize_text(graph_profile.get("state"), max_length=100),
                _normalize_text(graph_profile.get("country"), max_length=100),
                _normalize_text(manager_graph_object_id, max_length=150),
                Json(graph_profile),
            ),
        )


def sync_graph_groups_for_user(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
    graph_groups: dict[str, Any],
) -> None:
    """Map Microsoft Graph groups to teams and team_members idempotently."""
    groups = graph_groups.get("value", [])
    if not isinstance(groups, list):
        raise ValueError("Graph groups payload must contain a list in 'value'.")

    for group in groups:
        if not isinstance(group, dict):
            continue
        odata_type = str(group.get("@odata.type") or "").strip()
        if odata_type and odata_type != "#microsoft.graph.group":
            continue

        team_key = _required_text(str(group.get("id") or ""), field_name="team_key", max_length=100)
        team_name = _normalize_text(group.get("displayName"), max_length=200) or team_key

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO teams (
                    tenant_id,
                    team_key,
                    team_name,
                    source
                )
                VALUES (%s, %s, %s, 'GRAPH')
                ON CONFLICT (tenant_id, team_key) DO UPDATE
                SET team_name = EXCLUDED.team_name,
                    source = EXCLUDED.source,
                    updated_at = NOW()
                RETURNING id::text AS team_id
                """,
                (tenant_id, team_key, team_name),
            )
            team = cur.fetchone()
            if team is None:
                raise LookupError(f"Graph team '{team_key}' could not be resolved.")

            cur.execute(
                """
                INSERT INTO team_members (
                    tenant_id,
                    team_id,
                    user_id,
                    member_role
                )
                VALUES (%s, %s, %s, 'MEMBER')
                ON CONFLICT (tenant_id, team_id, user_id) DO NOTHING
                """,
                (tenant_id, team["team_id"], user_id),
            )


def fetch_favorite_seat(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                s.id::text AS seat_id,
                s.seat_code,
                COUNT(*) AS booking_count
            FROM bookings b
            JOIN seats s
                ON s.id = b.seat_id
                AND s.tenant_id = b.tenant_id
            WHERE b.tenant_id = %s
              AND b.user_id = %s
              AND b.booking_status = 'CONFIRMED'
            GROUP BY s.id, s.seat_code
            ORDER BY booking_count DESC, s.id
            LIMIT 1
            """,
            (tenant_id, user_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def fetch_days_in_office(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT booking_date)
            FROM bookings
            WHERE tenant_id = %s
              AND user_id = %s
              AND booking_status = 'CONFIRMED'
              AND booking_date <= CURRENT_DATE
            """,
            (tenant_id, user_id),
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0
def fetch_days_in_office_current_month(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT booking_date)
            FROM bookings
            WHERE tenant_id = %s
              AND user_id = %s
              AND booking_status IN ('CONFIRMED', 'CHECKED_IN', 'COMPLETED')
              AND booking_date <= CURRENT_DATE
              AND DATE_TRUNC('month', booking_date)
                    = DATE_TRUNC('month', CURRENT_DATE)
            """,
            (tenant_id, user_id),
        )

        row = cur.fetchone()

    return int(row[0]) if row else 0
def fetch_days_in_office_current_year(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT booking_date)
            FROM bookings
            WHERE tenant_id = %s
              AND user_id = %s
              AND booking_status IN ('CONFIRMED', 'CHECKED_IN', 'COMPLETED')
              AND booking_date <= CURRENT_DATE
              AND DATE_TRUNC('year', booking_date)
                    = DATE_TRUNC('year', CURRENT_DATE)
            """,
            (tenant_id, user_id),
        )

        row = cur.fetchone()

    return int(row[0]) if row else 0
def fetch_team_rank_current_year(
    conn: PGConnection,
    *,
    tenant_id: str,
    user_id: str,
) -> dict[str, int | None]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            WITH primary_team AS (
                SELECT MIN(tm.team_id) AS team_id
                FROM team_members tm
                WHERE tm.tenant_id = %s
                  AND tm.user_id = %s
            ),
            yearly_counts AS (
                SELECT
                    tm.user_id::text AS user_id,
                    COUNT(DISTINCT b.booking_date) AS office_days
                FROM team_members tm
                CROSS JOIN primary_team pt
                LEFT JOIN bookings b
                    ON b.user_id = tm.user_id
                   AND b.tenant_id = tm.tenant_id
                   AND b.booking_status IN (
                        'CONFIRMED',
                        'CHECKED_IN',
                        'COMPLETED'
                   )
                   AND b.booking_date <= CURRENT_DATE
                   AND DATE_TRUNC('year', b.booking_date)
                        = DATE_TRUNC('year', CURRENT_DATE)
                WHERE tm.tenant_id = %s
                  AND tm.team_id = pt.team_id
                GROUP BY tm.user_id
            ),
            ranked AS (
                SELECT
                    user_id,
                    office_days,
                    RANK() OVER (
                        ORDER BY office_days DESC
                    ) AS team_rank
                FROM yearly_counts
            )
            SELECT
                team_rank,
                (
                    SELECT COUNT(*)
                    FROM yearly_counts
                ) AS team_member_count
            FROM ranked
            WHERE user_id = %s
            """,
            (
                tenant_id,
                user_id,
                tenant_id,
                user_id,
            ),
        )

        row = cur.fetchone()

    if row is None:
        return {
            "team_rank_current_year": None,
            "team_member_count": 0,
        }

    return {
        "team_rank_current_year": int(row["team_rank"]),
        "team_member_count": int(row["team_member_count"]),
    }