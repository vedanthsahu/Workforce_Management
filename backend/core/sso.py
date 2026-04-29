"""Microsoft SSO and Graph integration helpers.

This module encapsulates the OAuth authorization-code exchange with Microsoft,
ID token verification against tenant JWKS keys, and selected Microsoft Graph
API calls used by the backend's SSO flow.
"""

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
    """Structured exception used for OAuth and token-verification failures.

    The route layer converts this error directly into a public API response
    without needing to infer status codes or provider details from raw
    exceptions.
    """

    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error into the backend's public error shape.

        Returns:
            dict[str, Any]: Dictionary containing the stable error code,
            message, and optional detail payload.

        Side Effects:
            None.

        Failure Modes:
            None expected under normal runtime conditions.
        """
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class GraphAPIError(SSOError):
    """Structured exception for Microsoft Graph request failures."""

    pass


def build_auth_url() -> tuple[str, str]:
    """Create the Microsoft authorization URL and CSRF state token.

    Returns:
        tuple[str, str]: The redirect URL for Microsoft login and the generated
        opaque state value that should be stored client-side.

    Side Effects:
        Uses cryptographically secure randomness and reads cached settings.

    Failure Modes:
        Propagates configuration-loading errors if required OAuth settings are
        missing or invalid.
    """
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
    """Exchange a Microsoft authorization code for tokens.

    Args:
        code: Authorization code returned by Microsoft after user consent.

    Returns:
        dict[str, str]: Mapping containing the ``access_token`` and
        ``id_token`` issued by Microsoft.

    Side Effects:
        Performs an outbound HTTP POST to the Microsoft token endpoint.

    Failure Modes:
        Raises ``SSOError`` when the code is missing, the provider is
        unreachable, the response is unsuccessful, or required tokens are
        absent from the provider payload.
    """
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
    """Validate a Microsoft ID token against tenant signing keys.

    Args:
        id_token: Encoded Microsoft ID token.

    Returns:
        dict[str, Any]: Decoded and verified token claims.

    Side Effects:
        Fetches the current tenant JWKS document over the network.

    Failure Modes:
        Raises ``SSOError`` when the token is missing, expired, invalid, signed
        with an unknown key, or issued for the wrong tenant.
    """
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
    """Fetch the signed-in Microsoft user's profile from Graph.

    Args:
        access_token: Microsoft Graph bearer token.

    Returns:
        dict[str, Any]: Provider response for the ``/me`` endpoint.

    Side Effects:
        Performs an outbound HTTP GET to Microsoft Graph.

    Failure Modes:
        Raises ``GraphAPIError`` when the token is missing or the request
        cannot be completed successfully.
    """
    return _graph_get(
        access_token,
        "/me",
        params={
            "$select": "id,displayName,mail,userPrincipalName,jobTitle,department,companyName",
        },
    )


def fetch_graph_groups(access_token: str) -> dict[str, Any]:
    """Fetch Microsoft Graph group memberships for the signed-in user.

    Args:
        access_token: Microsoft Graph bearer token.

    Returns:
        dict[str, Any]: Provider response for the ``/me/memberOf`` endpoint.

    Side Effects:
        Performs an outbound HTTP GET to Microsoft Graph.

    Failure Modes:
        Raises ``GraphAPIError`` when the token is missing or the request
        cannot be completed successfully.
    """
    return _graph_get(
        access_token,
        "/me/memberOf",
        params={"$select": "id,displayName"},
    )


def fetch_graph_manager(access_token: str) -> dict[str, Any]:
    """Fetch the signed-in user's manager relationship from Microsoft Graph.

    Args:
        access_token: Microsoft Graph bearer token.

    Returns:
        dict[str, Any]: Provider response for the ``/me/manager`` endpoint.

    Side Effects:
        Performs an outbound HTTP GET to Microsoft Graph.

    Failure Modes:
        Raises ``GraphAPIError`` when the token is missing or the request
        cannot be completed successfully.
    """
    return _graph_get(access_token, "/me/manager")


def _fetch_jwks() -> dict[str, Any]:
    """Fetch the tenant JWKS document used to verify Microsoft ID tokens.

    Returns:
        dict[str, Any]: JWKS payload returned by Microsoft.

    Side Effects:
        Performs an outbound HTTP GET to the configured JWKS endpoint.

    Failure Modes:
        Raises ``SSOError`` if the provider is unreachable or the response does
        not contain at least one signing key.
    """
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
    """Select the JWKS entry matching the token's ``kid`` header.

    Args:
        id_token: Encoded Microsoft ID token.
        jwks: Previously fetched JWKS document.

    Returns:
        dict[str, Any]: Matching signing-key record from the JWKS payload.

    Side Effects:
        None.

    Failure Modes:
        Raises ``SSOError`` when the token header cannot be parsed or no
        corresponding signing key is found.
    """
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
    """Perform an authenticated GET request against Microsoft Graph.

    Args:
        access_token: Microsoft Graph bearer token.
        path: Endpoint path relative to the Graph base URL.
        params: Optional query parameters forwarded to Graph.

    Returns:
        dict[str, Any]: Parsed JSON payload returned by Graph.

    Side Effects:
        Performs an outbound HTTP GET request.

    Failure Modes:
        Raises ``GraphAPIError`` for missing access tokens, network failures,
        permission issues, missing resources, or other unsuccessful provider
        responses.
    """
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
    """Parse a provider response body into a dictionary when possible.

    Args:
        response: HTTP response returned by ``requests``.

    Returns:
        dict[str, Any]: JSON object payload, wrapped non-dict JSON content, or
        an empty dictionary when the response body is empty or invalid JSON.

    Side Effects:
        Consumes the response body for JSON decoding.

    Failure Modes:
        None. Invalid JSON is treated as an empty payload.
    """
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {"data": payload}


def _provider_error_details(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract provider-specific error fields for downstream API responses.

    Args:
        payload: Parsed provider response payload.

    Returns:
        dict[str, Any] | None: Reduced error details when recognizable provider
        error fields exist, otherwise the original payload or ``None``.

    Side Effects:
        None.

    Failure Modes:
        None. Missing or partial fields simply produce a smaller detail object.
    """
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
