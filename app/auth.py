# app/auth.py
import os
import secrets
import sys
from fastapi import APIRouter, Request
from starlette.config import Config
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from app.redis_client import redis_client

# Load .env
load_dotenv()

# Initialize OAuth
config = Config(".env")
oauth = OAuth(config)

# Register Google OAuth provider
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

router = APIRouter()

@router.get("/auth/{provider}")
async def oauth_login(request: Request, provider: str):
    """Redirect user to the provider's OAuth login page."""
    redirect_uri = request.url_for("auth_callback", provider=provider)
    client = oauth.create_client(provider)

    print("🔁 Redirect URI:", redirect_uri, file=sys.stdout, flush=True)
    print("🧩 GOOGLE_CLIENT_ID =", os.getenv("GOOGLE_CLIENT_ID"), file=sys.stdout, flush=True)

    # If client ID is None, environment isn’t being loaded correctly
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return {"error": "GOOGLE_CLIENT_ID not found. Check .env and deployment environment variables."}

    return await client.authorize_redirect(request, redirect_uri)

@router.get("/auth/{provider}/callback", name="auth_callback")
async def auth_callback(request: Request, provider: str):
    """Handle OAuth callback from provider."""
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    print("🔑 OAuth token response:", token, file=sys.stdout, flush=True)

    userinfo = None

    # ---- GOOGLE ----
    if provider == "google":
        # Try to extract user info safely
        userinfo = token.get("userinfo")
        if not userinfo:
            try:
                userinfo = await client.parse_id_token(request, token)
            except Exception as e:
                print("⚠️ Failed to parse id_token:", e, file=sys.stdout, flush=True)
                # fallback: fetch from userinfo endpoint
                resp = await client.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
                userinfo = resp.json()

    # ---- GITHUB ----
    elif provider == "github":
        resp = await client.get("user", token=token)
        userinfo = resp.json()

    print("👤 User info received:", userinfo, file=sys.stdout, flush=True)

    # Session management
    user_email = userinfo.get("email") or userinfo.get("login")
    session_id = f"session:{secrets.token_urlsafe(16)}"
    await redis_client.set(session_id, user_email, ex=7 * 24 * 3600)

    response = RedirectResponse(url="/dashboard")
    response.set_cookie("sessionid", session_id, httponly=True, samesite="lax")
    return response
