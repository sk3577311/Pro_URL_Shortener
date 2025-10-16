import os
import secrets
import sys
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.config import Config
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from app.redis_client import redis_client

# Load environment variables
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

# ----------------------------- #
# 🔐 1️⃣ LOGIN REDIRECT
# ----------------------------- #
@router.get("/auth/{provider}")
async def oauth_login(request: Request, provider: str):
    """Redirect user to provider login."""
    redirect_uri = request.url_for("auth_callback", provider=provider)
    client = oauth.create_client(provider)

    print("🔁 Redirect URI:", redirect_uri, file=sys.stdout, flush=True)
    print("🧩 GOOGLE_CLIENT_ID =", os.getenv("GOOGLE_CLIENT_ID"), file=sys.stdout, flush=True)

    if not os.getenv("GOOGLE_CLIENT_ID"):
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not found in environment"}, status_code=500)

    return await client.authorize_redirect(request, redirect_uri)


# ----------------------------- #
# 🎯 2️⃣ CALLBACK HANDLER
# ----------------------------- #
@router.get("/auth/{provider}/callback", name="auth_callback")
async def auth_callback(request: Request, provider: str):
    """Handle OAuth callback and create session."""
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    print("🔑 OAuth token response:", token, file=sys.stdout, flush=True)

    userinfo = None

    # ---- GOOGLE ----
    if provider == "google":
        userinfo = token.get("userinfo")
        if not userinfo:
            try:
                userinfo = await client.parse_id_token(request, token)
            except Exception as e:
                print("⚠️ Failed to parse id_token:", e, file=sys.stdout, flush=True)
                resp = await client.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
                userinfo = resp.json()

    print("👤 User info received:", userinfo, file=sys.stdout, flush=True)

    if not userinfo or "email" not in userinfo:
        return JSONResponse({"error": "Failed to retrieve user information"}, status_code=400)

    # ----------------------------- #
    # 🧠 Create session and store user
    # ----------------------------- #
    user_email = userinfo.get("email")
    avatar = userinfo.get("picture")

    session_id = f"session:{secrets.token_urlsafe(16)}"
    await redis_client.set(session_id, user_email, ex=7 * 24 * 3600)
    if avatar:
        await redis_client.set(f"{session_id}:avatar", avatar, ex=7 * 24 * 3600)

    # Redirect to homepage after successful login
    response = RedirectResponse(url="/")
    response.set_cookie("sessionid", session_id, httponly=True, samesite="lax")
    return response


# ----------------------------- #
# 👤 3️⃣ USER SESSION CHECK
# ----------------------------- #
@router.get("/auth/me")
async def get_logged_in_user(request: Request):
    """Return current logged-in user info."""
    session_id = request.cookies.get("sessionid")
    if not session_id:
        return JSONResponse({"logged_in": False})

    user_email = await redis_client.get(session_id)
    if not user_email:
        return JSONResponse({"logged_in": False})

    avatar = await redis_client.get(f"{session_id}:avatar")

    return JSONResponse({
        "logged_in": True,
        "email": user_email,
        "avatar": avatar,
    })
