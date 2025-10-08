# app/main.py
import os
import re
import secrets
import string
from datetime import datetime
from typing import Optional
from pathlib import Path
# fastapi imports
from fastapi import FastAPI, HTTPException, Request, status, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.redis_client import init_redis_pool, redis_client,close_redis
                
# ----------------------------
# Template setup
# ----------------------------
templates = Jinja2Templates(directory="templates")

# ----------------------------
# Lifespan for Redis connection
# ----------------------------
@asynccontextmanager
async def lifespan_redis(app: FastAPI):
    # Startup: Initialize Redis
    client = await init_redis_pool()
    globals()["redis_client"] = client
    try:
        yield
    except Exception as error:
        print("Error during app lifespan:", error)
    await close_redis()
    
    
# ----------------------------
# Alias validation
# ----------------------------
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,100}$")

def valid_alias(alias: str) -> bool:
    return bool(ALIAS_RE.fullmatch(alias))

            
app = FastAPI(title="URL Shortener (FastAPI + Redis)",lifespan=lifespan_redis,debug=True)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent.absolute() / "static"),
    name="static",
)

# ----------------------------
# Helper: Client ID for rate limiting
# ----------------------------
def get_client_id(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "anonymous"

# --------------
# ttl conversion
# --------------
def format_ttl(ttl: int) -> str:
    """Convert seconds to a readable duration (e.g., '2 hours', '1 day')."""
    if ttl == 0:
        return "as long as you want"
    else:
        days = ttl // 86400
        return f"{days} day{'s' if days != 1 else ''}"

# ----------------------------
# Simple rate limiter (10 req/min)
# ----------------------------
async def check_rate_limit(client_id: str, limit: int = 10, period_seconds:int=60):
    from app.redis_client import redis_client  # ensure you're using the same instance
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not initialized")
    print("Redis client:", redis_client)
    key = f"rate:{client_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, period_seconds)
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

# ----------------------------
# Homepage (form)
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render the HTML form to input a long URL."""
    return templates.TemplateResponse("index.html", {"request": request, "short_url": None, "error": None})

# ----------------------------
# POST /shorten (Form submission)
# ----------------------------
@app.post("/shorten", response_class=HTMLResponse)
async def shorten_url(
    request: Request,
    original_url: str = Form(...),
    custom_alias: Optional[str] = Form(None),
    ttl: int = Form(...)
):
    client_id = get_client_id(request)
    await check_rate_limit(client_id, limit=10, period_seconds=ttl)

    # Normalize URL
    if not original_url.startswith(("http://", "https://")):
        original_url = "http://" + original_url
    long_url = original_url.strip()
    created_at = datetime.utcnow().isoformat()

    # --- Handle custom alias ---
    if custom_alias:
        custom_alias = custom_alias.strip()
        if not valid_alias(custom_alias):
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "short_url": None, "error": "Invalid alias. Use A-Z, a-z, 0-9, _ or -"}
            )
        ok = await redis_client.set(f"url:{custom_alias}", long_url, nx=True, ex=ttl)
        if not ok:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "short_url": None, "error": "Alias already in use."}
            )
        short_code = custom_alias
    else:
        # --- Generate random 6-character code ---
        alphabet = string.ascii_letters + string.digits
        while True:
            short_code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not await redis_client.exists(f"url:{short_code}"):
                break
    # --- Store main URL ---
    if ttl and int(ttl) > 0:
        await redis_client.setex(f"url:{short_code}", int(ttl), long_url)
    else:
        await redis_client.set(f"url:{short_code}", long_url)

    # --- Metadata ---
    await redis_client.hset(
        f"meta:{short_code}",
        mapping={"created_at": created_at, "owner": client_id, "ttl": ttl}
    )
    if ttl and int(ttl) > 0:
        await redis_client.expire(f"meta:{short_code}", int(ttl))

    # --- Click counter ---
    await redis_client.set(f"clicks:{short_code}", 0)
    if ttl and int(ttl) > 0:
        await redis_client.expire(f"clicks:{short_code}", int(ttl))

    # --- Optional: rate limit key per URL ---
    if ttl and int(ttl) > 0:
        await redis_client.setex(f"rate:{client_id}:{short_code}", int(ttl), 0)
    else:
        await redis_client.set(f"rate:{client_id}:{short_code}", 0)
    
    readable_ttl = format_ttl(ttl)

    short_url = str(request.base_url).rstrip("/") + "/" + short_code
    readable_ttl = format_ttl(ttl)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "short_url": short_url, "error": None,"readable_ttl":readable_ttl}
    )
# ----------------------------
# Redirect /{short_code}
# ----------------------------
@app.get("/{short_code}")
async def redirect_short(short_code: str):
    global redis_client
    long_url = await redis_client.get(f"url:{short_code}")
    if not long_url:
        raise HTTPException(status_code=404, detail="This short URL has expired or doesn't exist.")
    await redis_client.incr(f"clicks:{short_code}")
    return RedirectResponse(url=long_url)


@app.get("/stats/{short_code}")
async def stats(short_code: str):
    long_url = await redis_client.get(f"url:{short_code}")
    if not long_url:
        raise HTTPException(status_code=404, detail="Short code not found.")
    clicks = await redis_client.get(f"clicks:{short_code}") or 0
    meta = await redis_client.hgetall(f"meta:{short_code}")
    return {
        "short_code": short_code,
        "long_url": long_url,
        "clicks": int(clicks),
        "meta": meta
    }
