from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from jose import ExpiredSignatureError, JWTError, jwt

from backend.core.config import get_settings

MICROSOFT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
STATE_TTL_SECONDS = 600
MICROSOFT_SCOPES = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "User.Read",
    "User.Read.All",
    "GroupMember.Read.All",
)


@dataclass(frozen=True)
class SSOError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class GraphAPIError(SSOError):
    pass


def build_auth_url() -> tuple[str, str]:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.client_id,
            "response_type": "code",
            "redirect_uri": settings.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(MICROSOFT_SCOPES),
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{settings.auth_url}?{query}", state


def exchange_code_for_token(code: str) -> dict[str, str]:
    settings = get_settings()
    if not code:
        raise SSOError(
            status_code=400,
            code="missing_authorization_code",
            message="Microsoft callback did not include an authorization code.",
        )

    try:
        response = requests.post(
            settings.token_url,
            data={
                "client_id": settings.client_id,
                "client_secret": settings.client_secret,
                "code": code,
                "redirect_uri": settings.redirect_uri,
                "grant_type": "authorization_code",
                "scope": " ".join(MICROSOFT_SCOPES),
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise SSOError(
            status_code=502,
            code="token_exchange_unavailable",
            message="Failed to reach Microsoft token endpoint.",
        ) from exc

    payload = _safe_json(response)
    if response.status_code != 200:
        raise SSOError(
            status_code=400,
            code="token_exchange_failed",
            message="Microsoft token exchange failed.",
            details=_provider_error_details(payload),
        )

    access_token = payload.get("access_token")
    id_token = payload.get("id_token")
    if not access_token:
        raise SSOError(
            status_code=400,
            code="missing_access_token",
            message="Microsoft token response did not include an access_token.",
            details=_provider_error_details(payload),
        )
    if not id_token:
        raise SSOError(
            status_code=400,
            code="missing_id_token",
            message="Microsoft token response did not include an id_token.",
            details=_provider_error_details(payload),
        )

    return {
        "access_token": str(access_token),
        "id_token": str(id_token),
    }


def verify_id_token(id_token: str) -> dict[str, Any]:
    settings = get_settings()
    if not id_token:
        raise SSOError(
            status_code=401,
            code="missing_id_token",
            message="Microsoft id_token is required.",
        )

    jwks = _fetch_jwks()
    signing_key = _resolve_signing_key(id_token, jwks)

    try:
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.client_id,
            issuer=f"https://login.microsoftonline.com/{settings.tenant_id}/v2.0",
        )
    except ExpiredSignatureError as exc:
        raise SSOError(
            status_code=401,
            code="expired_id_token",
            message="Microsoft id_token has expired.",
        ) from exc
    except JWTError as exc:
        raise SSOError(
            status_code=401,
            code="invalid_id_token",
            message="Microsoft id_token validation failed.",
        ) from exc

    if str(claims.get("tid") or "") != settings.tenant_id:
        raise SSOError(
            status_code=401,
            code="tenant_mismatch",
            message="Microsoft id_token tenant did not match the configured tenant.",
        )

    return claims


def fetch_graph_me(access_token: str) -> dict[str, Any]:
    return _graph_get(
        access_token,
        "/me",
        params={
            "$select": "id,displayName,mail,userPrincipalName,jobTitle,department,companyName",
        },
    )


def fetch_graph_groups(access_token: str) -> dict[str, Any]:
    return _graph_get(
        access_token,
        "/me/memberOf",
        params={"$select": "id,displayName"},
    )


def fetch_graph_manager(access_token: str) -> dict[str, Any]:
    return _graph_get(access_token, "/me/manager")


def _fetch_jwks() -> dict[str, Any]:
    settings = get_settings()
    try:
        response = requests.get(settings.jwks_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SSOError(
            status_code=502,
            code="jwks_fetch_failed",
            message="Failed to fetch Microsoft signing keys.",
        ) from exc

    payload = _safe_json(response)
    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        raise SSOError(
            status_code=502,
            code="invalid_jwks_response",
            message="Microsoft JWKS response did not contain any signing keys.",
        )
    return payload


def _resolve_signing_key(id_token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise SSOError(
            status_code=401,
            code="invalid_id_token_header",
            message="Microsoft id_token header is invalid.",
        ) from exc

    kid = str(header.get("kid") or "")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise SSOError(
        status_code=401,
        code="signing_key_not_found",
        message="No matching Microsoft signing key was found for the id_token.",
    )


def _graph_get(
    access_token: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not access_token:
        raise GraphAPIError(
            status_code=401,
            code="missing_access_token",
            message="Session is missing the Microsoft access token.",
        )

    try:
        response = requests.get(
            f"{MICROSOFT_GRAPH_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=10,
        )
    except requests.RequestException as exc:
        raise GraphAPIError(
            status_code=502,
            code="graph_unavailable",
            message="Failed to reach Microsoft Graph.",
        ) from exc

    payload = _safe_json(response)
    if response.status_code == 403:
        raise GraphAPIError(
            status_code=403,
            code="insufficient_privileges",
            message="The signed-in user or app does not have enough Microsoft Graph permissions.",
            details=_provider_error_details(payload),
        )
    if response.status_code == 404:
        raise GraphAPIError(
            status_code=404,
            code="graph_resource_not_found",
            message="The requested Microsoft Graph resource was not found.",
            details=_provider_error_details(payload),
        )
    if response.status_code >= 400:
        raise GraphAPIError(
            status_code=502 if response.status_code >= 500 else response.status_code,
            code="graph_request_failed",
            message="Microsoft Graph request failed.",
            details=_provider_error_details(payload),
        )

    return payload


def _safe_json(response: requests.Response) -> dict[str, Any]:
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {"data": payload}


def _provider_error_details(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not payload:
        return None

    details: dict[str, Any] = {}
    error = payload.get("error")
    error_description = payload.get("error_description")

    if isinstance(error, str) and error:
        details["provider_error"] = error
    elif isinstance(error, dict):
        if error.get("code"):
            details["provider_error"] = error["code"]
        if error.get("message"):
            details["provider_message"] = error["message"]

    if isinstance(error_description, str) and error_description:
        details["provider_message"] = error_description

    return details or payload
