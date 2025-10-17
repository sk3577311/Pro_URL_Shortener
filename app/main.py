import os
import re
import string, secrets
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.redis_client import redis_client
from app.auth import router as auth_router

# ----------------------------
# App setup
# ----------------------------
app = FastAPI(title="URL Shortener (FastAPI + Upstash Redis)")
templates = Jinja2Templates(directory="templates")

# Serve static files
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent.absolute() / "static"),
    name="static",
)

# Session middleware for cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "supersecretkey"),
    same_site="lax",
    https_only=False  # Set to True in production (with HTTPS)
)

# Include OAuth routes
app.include_router(auth_router)

# ----------------------------
# Helpers
# ----------------------------
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,100}$")

def valid_alias(alias: str) -> bool:
    return bool(ALIAS_RE.fullmatch(alias))

def get_client_id(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "anonymous"

def format_ttl(ttl: int) -> str:
    if ttl == 0:
        return "as long as you want"
    days = ttl // 86400
    return f"{days} day{'s' if days != 1 else ''}"

def check_rate_limit(client_id: str, limit: int = 5, period_seconds: int = 60):
    key = f"rate:{client_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, period_seconds)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: Only {limit} requests allowed per {period_seconds} seconds."
        )

# ----------------------------
# Helper: Get logged-in user
# ----------------------------
async def get_logged_in_user(request: Request):
    session_id = request.cookies.get("sessionid")
    if not session_id:
        return None
    email = redis_client.get(session_id)
    avatar = redis_client.get(f"{session_id}:avatar")
    if not email:
        return None
    return {"email": email, "avatar_url": avatar}

# ----------------------------
# Pages
# ----------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Get session
    session_id = request.cookies.get("sessionid")
    user = None

    if session_id:
        email = redis_client.get(session_id)
        avatar = redis_client.get(f"{session_id}:avatar")
        if email:
            user = {"email": email, "avatar_url": avatar}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "short_url": None,
            "error": None,
            "logged_in_user": user,  # ✅ consistent naming for templates
        }
    )
@app.get("/pricing")
async def pricing(request: Request):
    logged_in_user = await get_logged_in_user(request)
    return templates.TemplateResponse("pricing.html", {"request": request, "logged_in_user": logged_in_user})

@app.get("/about")
async def about(request: Request):
    logged_in_user = await get_logged_in_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "logged_in_user": logged_in_user})

@app.get("/auth")
async def login_page(request: Request):
    logged_in_user = await get_logged_in_user(request)
    if logged_in_user:
        return RedirectResponse(url="/")  # Already logged in
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/signup")
async def signup_page(request: Request):
    logged_in_user = await get_logged_in_user(request)
    if logged_in_user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("signup.html", {"request": request})

# ----------------------------
# POST /shorten — requires login
# ----------------------------
@app.post("/shorten", response_class=HTMLResponse)
async def shorten_url(
    request: Request,
    original_url: str = Form(...),
    custom_alias: Optional[str] = Form(None),
    ttl: int = Form(...),
):
    # 🔒 Require login
    session_id = request.cookies.get("sessionid")
    if not session_id:
        return RedirectResponse(url="/login", status_code=303)

    email = redis_client.get(session_id)
    avatar = redis_client.get(f"{session_id}:avatar")
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    logged_in_user = {"email": email, "avatar_url": avatar}
    client_id = get_client_id(request)

    try:
        check_rate_limit(client_id, limit=5, period_seconds=60)
    except HTTPException as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "short_url": None, "error": e.detail, "logged_in_user": logged_in_user},
        )

    # Normalize URL
    if not original_url.startswith(("http://", "https://")):
        original_url = "http://" + original_url
    long_url = original_url.strip()
    created_at = datetime.utcnow().isoformat()

    # Handle alias or random code
    if custom_alias:
        custom_alias = custom_alias.strip()
        if not valid_alias(custom_alias):
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "short_url": None,
                    "error": "Invalid alias (A-Z, a-z, 0-9, _ or - only).",
                    "logged_in_user": logged_in_user,
                },
            )
        ok = redis_client.set(f"url:{custom_alias}", long_url, nx=True, ex=ttl)
        if not ok:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "short_url": None,
                    "error": "Alias already in use.",
                    "logged_in_user": logged_in_user,
                },
            )
        short_code = custom_alias
    else:
        alphabet = string.ascii_letters + string.digits
        while True:
            short_code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not redis_client.exists(f"url:{short_code}"):
                break
        if ttl and ttl > 0:
            redis_client.set(f"url:{short_code}", long_url, ex=ttl)
        else:
            redis_client.set(f"url:{short_code}", long_url)

    # Store metadata
    redis_client.hmset(
        f"meta:{short_code}",
        {"created_at": created_at, "owner": logged_in_user["email"], "ttl": ttl}
    )
    if ttl and ttl > 0:
        redis_client.expire(f"meta:{short_code}", ttl)

    # Click counter
    redis_client.set(f"clicks:{short_code}", 0)

    readable_ttl = format_ttl(ttl)
    short_url = str(request.base_url).rstrip("/") + "/" + short_code

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "short_url": short_url,
            "error": None,
            "readable_ttl": readable_ttl,
            "logged_in_user": logged_in_user,
        },
    )

# ----------------------------
# Redirect short URL
# ----------------------------
@app.get("/{short_code}")
async def redirect_short(short_code: str):
    long_url = redis_client.get(f"url:{short_code}")
    if not long_url:
        raise HTTPException(status_code=404, detail="This short URL has expired or doesn't exist.")
    redis_client.incr(f"clicks:{short_code}")
    return RedirectResponse(url=long_url)

# ----------------------------
# Stats endpoint
# ----------------------------
@app.get("/stats/{short_code}")
async def stats(short_code: str):
    long_url = redis_client.get(f"url:{short_code}")
    if not long_url:
        raise HTTPException(status_code=404, detail="Short code not found.")
    clicks = redis_client.get(f"clicks:{short_code}") or 0
    meta = redis_client.hgetall(f"meta:{short_code}")
    return {"short_code": short_code, "long_url": long_url, "clicks": int(clicks), "meta": meta}

# ----------------------------
# Analytics page
# ----------------------------
@app.get("/analytics/{code}", response_class=HTMLResponse)
async def analytics_page(request: Request, code: str):
    meta = redis_client.hgetall(f"meta:{code}") or {}
    clicks = redis_client.get(f"clicks:{code}") or 0
    logged_in_user = await get_logged_in_user(request)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "code": code, "meta": meta, "clicks": int(clicks), "logged_in_user": logged_in_user},
    )
