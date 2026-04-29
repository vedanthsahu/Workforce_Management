"""Runtime configuration loading for the backend service.

This module centralizes environment-variable parsing and exposes an immutable
``Settings`` object consumed throughout the application. It is responsible for
loading local ``.env`` values during startup, coercing configuration into the
expected types, applying compatibility defaults for older JWT settings, and
deriving Microsoft OAuth endpoint URLs from the configured tenant.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load local development environment variables during import so application and
# CLI entrypoints resolve settings from the same source of truth.
load_dotenv()


def _require_env(name: str) -> str:
    """Return a required environment variable.

    Args:
        name: Name of the environment variable to read.

    Returns:
        str: The configured value.

    Side Effects:
        Reads from the current process environment.

    Failure Modes:
        Raises ``RuntimeError`` if the variable is unset or empty.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_int_env(name: str, default: str) -> int:
    """Parse an integer-valued environment variable.

    Args:
        name: Name of the environment variable to read.
        default: Fallback string value used when the variable is absent.

    Returns:
        int: The parsed integer value.

    Side Effects:
        Reads from the current process environment.

    Failure Modes:
        Raises ``RuntimeError`` if the value cannot be parsed as an integer.
    """
    raw_value = os.getenv(name, default)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _parse_bool_env(name: str, default: bool) -> bool:
    """Parse a boolean-valued environment variable.

    Args:
        name: Name of the environment variable to read.
        default: Fallback value used when the variable is absent.

    Returns:
        bool: The normalized boolean value.

    Side Effects:
        Reads from the current process environment.

    Failure Modes:
        Raises ``RuntimeError`` if the value is present but does not match one
        of the accepted boolean spellings.
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean")


def _parse_list_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Parse a comma-delimited environment variable into a tuple.

    Args:
        name: Name of the environment variable to read.
        default: Fallback tuple used when the variable is absent.

    Returns:
        tuple[str, ...]: The normalized sequence of non-empty values.

    Side Effects:
        Reads from the current process environment.

    Failure Modes:
        Raises ``RuntimeError`` if the variable is present but does not contain
        any non-empty entries after trimming.
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not values:
        raise RuntimeError(f"{name} must contain at least one value")
    return values


def _parse_samesite_env(name: str, default: str) -> str:
    """Parse a cookie ``SameSite`` policy from the environment.

    Args:
        name: Name of the environment variable to read.
        default: Fallback value used when the variable is absent.

    Returns:
        str: One of ``"lax"``, ``"strict"``, or ``"none"``.

    Side Effects:
        Reads from the current process environment.

    Failure Modes:
        Raises ``RuntimeError`` if the configured value is outside the allowed
        set of cookie policies.
    """
    value = os.getenv(name, default).strip().lower()
    if value not in {"lax", "strict", "none"}:
        raise RuntimeError(f"{name} must be one of: lax, strict, none")
    return value


def _is_https_url(url: str) -> bool:
    """Determine whether a configured URL uses HTTPS.

    Args:
        url: URL string to inspect.

    Returns:
        bool: ``True`` when the parsed scheme is HTTPS.

    Side Effects:
        None.

    Failure Modes:
        None. Invalid or scheme-less URLs simply return ``False``.
    """
    return urlparse(url).scheme.lower() == "https"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration for the backend application.

    Instances of this dataclass are created once by :func:`get_settings` and
    then shared across the process. The attributes combine raw environment
    values with derived fields such as OAuth endpoint URLs and PostgreSQL
    connection settings.
    """

    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int
    db_sslmode: str
    db_connect_timeout: int
    jwt_secret: str
    jwt_algorithm: str
    jwt_access_token_ttl: int
    jwt_refresh_token_ttl: int
    jwt_allowed_claims: tuple[str, ...]
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    client_id: str
    client_secret: str
    tenant_id: str
    redirect_uri: str
    frontend_url: str
    session_ttl: int
    auth_url: str
    token_url: str
    jwks_url: str

    @property
    def db_config(self) -> dict[str, object]:
        """Return connection arguments expected by ``psycopg2.connect``.

        Returns:
            dict[str, object]: Keyword arguments suitable for establishing a
            PostgreSQL connection.

        Side Effects:
            None.

        Failure Modes:
            None. The property only exposes already-validated configuration.
        """
        return {
            "host": self.db_host,
            "dbname": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "port": self.db_port,
            "sslmode": self.db_sslmode,
            "connect_timeout": self.db_connect_timeout,
        }


@lru_cache
def get_settings() -> Settings:
    """Build and cache the backend settings object.

    The function is process-global and memoized so repeated callers share one
    immutable configuration snapshot instead of reparsing environment variables
    on every request.

    Returns:
        Settings: Parsed and derived runtime configuration.

    Side Effects:
        Reads environment variables and may load compatibility defaults from the
        legacy ``JWT_EXPIRE_HOURS`` setting when the newer access-token TTL is
        not provided.

    Failure Modes:
        Raises ``RuntimeError`` when required variables are missing or when any
        typed setting cannot be parsed.
    """
    tenant_id = _require_env("TENANT_ID")
    frontend_url = _require_env("FRONTEND_URL").rstrip("/")
    redirect_uri = _require_env("REDIRECT_URI")
    access_token_ttl = os.getenv("JWT_ACCESS_TOKEN_TTL")
    if access_token_ttl is None:
        legacy_expire_hours = os.getenv("JWT_EXPIRE_HOURS")
        # Preserve compatibility with older deployments that still configure
        # access-token duration in hours instead of seconds.
        access_token_ttl = (
            str(_parse_int_env("JWT_EXPIRE_HOURS", "1") * 3600)
            if legacy_expire_hours is not None
            else "900"
        )

    # Default secure cookies when either the frontend or OAuth callback uses
    # HTTPS, while still allowing explicit environment overrides.
    cookie_secure_default = _is_https_url(frontend_url) or _is_https_url(redirect_uri)

    return Settings(
        db_host=_require_env("DB_HOST"),
        db_name=_require_env("DB_NAME"),
        db_user=_require_env("DB_USER"),
        db_password=_require_env("DB_PASSWORD"),
        db_port=_parse_int_env("DB_PORT", "5432"),
        db_sslmode=os.getenv("DB_SSLMODE", "require"),
        db_connect_timeout=_parse_int_env("DB_CONNECT_TIMEOUT", "10"),
        jwt_secret=_require_env("JWT_SECRET"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_token_ttl=_parse_int_env("JWT_ACCESS_TOKEN_TTL", access_token_ttl),
        jwt_refresh_token_ttl=_parse_int_env("JWT_REFRESH_TOKEN_TTL", str(30 * 24 * 60 * 60)),
        jwt_allowed_claims=_parse_list_env(
            "JWT_ALLOWED_CLAIMS",
            ("sub", "email", "role", "tenant", "iat", "exp"),
        ),
        auth_cookie_secure=_parse_bool_env("AUTH_COOKIE_SECURE", cookie_secure_default),
        auth_cookie_samesite=_parse_samesite_env("AUTH_COOKIE_SAMESITE", "lax"),
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        frontend_url=frontend_url,
        session_ttl=_parse_int_env("SESSION_TTL", "3600"),
        auth_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        jwks_url=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
    )
