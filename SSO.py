import secrets
import time
import logging
import requests

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import ExpiredSignatureError, JWTError, jwt

# ───────────────── CONFIG ─────────────────

PUBLIC_BASE_URL = "http://localhost:8000"  # change to ngrok URL when testing externally

PUBLIC_BASE_URL = "http://localhost:8000"

SESSION_TTL = 3600
STATE_TTL   = 600

REDIRECT_URI = f"{PUBLIC_BASE_URL}/auth/callback"
AUTH_URL     = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize"
TOKEN_URL    = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
JWKS_URL     = f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"

IS_LOCALHOST = True

# ───────────────── LOGGING ─────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sso")

# ───────────────── STORAGE ─────────────────
sessions = {}
login_states = {}

# ───────────────── APP ─────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────── HELPERS ─────────────────

def _verify_id_token(id_token: str) -> dict:
    jwks = requests.get(JWKS_URL).json()
    claims = jwt.decode(
        id_token,
        jwks,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        options={"verify_iss": False},
    )
    return claims


def _build_auth_url():
    state = secrets.token_urlsafe(16)
    login_states[state] = time.time()

    url = (
        f"{AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid profile email https://graph.microsoft.com/User.Read"
        f"&state={state}"
    )
    return url, state


def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        raise HTTPException(401, "Not authenticated")
    return sessions[token]

# ───────────────── ROUTES ─────────────────

@app.get("/auth/login-page", response_class=HTMLResponse)
def login_page():
    url, _ = _build_auth_url()
    return HTMLResponse(f"<script>window.location='{url}'</script>")


@app.get("/auth/callback")
def callback(code: str, state: str):
    if state not in login_states:
        raise HTTPException(400, "Invalid state")

    # TOKEN EXCHANGE
    token_res = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": "https://graph.microsoft.com/.default",
        },
    )

    if token_res.status_code != 200:
        raise HTTPException(400, token_res.text)

    token_data = token_res.json()

    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")

    if not access_token:
        raise HTTPException(400, "No access_token returned")

    claims = _verify_id_token(id_token)

    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        "user_id": claims.get("oid"),
        "email": claims.get("preferred_username"),
        "claims": claims,
        "access_token": access_token,
        "created_at": time.time(),
    }

    resp = RedirectResponse(url="/welcome")
    resp.set_cookie("session_token", session_token, httponly=True)
    return resp


@app.get("/me")
def me(user=Depends(get_current_user)):
    return user


# 🔥 GRAPH CALL
@app.get("/graph/me")
def graph_me(user=Depends(get_current_user)):
    token = user["access_token"]

    url = "https://graph.microsoft.com/v1.0/me?$select=id,displayName,mail,jobTitle,department,companyName"

    res = requests.get(url, headers={
        "Authorization": f"Bearer {token}"
    })

    return {
        "status": res.status_code,
        "data": res.json()
    }
@app.get("/graph/manager")
def graph_manager(user=Depends(get_current_user)):
    token = user["access_token"]

    res = requests.get(
        "https://graph.microsoft.com/v1.0/me/manager",
        headers={"Authorization": f"Bearer {token}"}
    )

    if res.status_code != 200:
        return {
            "status": res.status_code,
            "message": "Manager not assigned OR permission missing",
            "error": res.json()
        }

    return res.json()

@app.get("/graph/groups")
def graph_groups(user=Depends(get_current_user)):
    token = user["access_token"]

    url = "https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName"

    res = requests.get(url, headers={
        "Authorization": f"Bearer {token}"
    })

    return {
        "status": res.status_code,
        "data": res.json()
    }
@app.get("/graph/direct-reports")
def graph_reports(user=Depends(get_current_user)):
    token = user["access_token"]

    res = requests.get(
        "https://graph.microsoft.com/v1.0/me/directReports",
        headers={"Authorization": f"Bearer {token}"}
    )

    return {
        "status": res.status_code,
        "data": res.json()
    }
@app.get("/graph/raw-user")
def graph_raw_user(user=Depends(get_current_user)):
    token = user["access_token"]

    url = f"https://graph.microsoft.com/v1.0/users/{user['user_id']}"

    res = requests.get(url, headers={
        "Authorization": f"Bearer {token}"
    })

    return {
        "status": res.status_code,
        "data": res.json()
    }
@app.get("/welcome", response_class=HTMLResponse)
def welcome():
    return HTMLResponse("""
    <h2>Login successful</h2>
    <a href="/me">/me</a><br>
    <a href="/graph/me">/graph/me</a>
    """)