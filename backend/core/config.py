import os
from dataclasses import dataclass
from functools import lru_cache

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
    jwt_expire_hours: int
    # SSO: Microsoft OAuth2/OIDC client configuration.
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    public_base_url: str

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
        jwt_expire_hours=_parse_int_env("JWT_EXPIRE_HOURS", "1"),
        # SSO: Azure application credentials and callback base URL.
        azure_client_id=_require_env("AZURE_CLIENT_ID"),
        azure_client_secret=_require_env("AZURE_CLIENT_SECRET"),
        azure_tenant_id=_require_env("AZURE_TENANT_ID"),
        public_base_url=_require_env("PUBLIC_BASE_URL"),
    )
