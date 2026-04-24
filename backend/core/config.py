import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_int_env(name: str, default: str) -> int:
    raw_value = os.getenv(name, default)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _parse_bool_env(name: str, default: bool) -> bool:
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
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not values:
        raise RuntimeError(f"{name} must contain at least one value")
    return values


def _parse_samesite_env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in {"lax", "strict", "none"}:
        raise RuntimeError(f"{name} must be one of: lax, strict, none")
    return value


def _is_https_url(url: str) -> bool:
    return urlparse(url).scheme.lower() == "https"


@dataclass(frozen=True)
class Settings:
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
    tenant_id = _require_env("TENANT_ID")
    frontend_url = _require_env("FRONTEND_URL").rstrip("/")
    redirect_uri = _require_env("REDIRECT_URI")
    access_token_ttl = os.getenv("JWT_ACCESS_TOKEN_TTL")
    if access_token_ttl is None:
        legacy_expire_hours = os.getenv("JWT_EXPIRE_HOURS")
        access_token_ttl = (
            str(_parse_int_env("JWT_EXPIRE_HOURS", "1") * 3600)
            if legacy_expire_hours is not None
            else "900"
        )

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
