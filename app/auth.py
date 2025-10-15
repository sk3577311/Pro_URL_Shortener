# app/auth.py
import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Request
from app.redis_client import redis_client  # optional for session store

config = Config(".env")
oauth = OAuth(config)

# register providers (use your env vars)
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

oauth.register(
    name='github',
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

router = APIRouter()

@router.get("/auth/{provider}")
async def oauth_login(request: Request, provider: str):
    redirect_uri = request.url_for("auth_callback", provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)

@router.get("/auth/{provider}/callback", name="auth_callback")
async def auth_callback(request: Request, provider: str):
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    if provider == "google":
        userinfo = await client.parse_id_token(request, token)
    else:
        # github: fetch user
        userinfo = await client.get("user", token=token)
        userinfo = userinfo.json()
    # userinfo now contains email, name, id...
    # Create or fetch user in your DB, create session cookie
    # Example: set session in Redis (pseudo)
    user_email = userinfo.get("email") or userinfo.get("login")
    session_id = f"session:{secrets.token_urlsafe(16)}"
    await redis_client.set(session_id, user_email, ex=7*24*3600)
    response = RedirectResponse(url="/dashboard")
    response.set_cookie("sessionid", session_id, httponly=True, samesite="lax")
    return response
