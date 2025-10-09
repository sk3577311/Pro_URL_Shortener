# app/main.py
import os
import re
import string, secrets
from datetime import datetime
from typing import Optional
from pathlib import Path
# fastapi imports
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# Upstash Redis client
from app.redis_client import redis_client


# ----------------------------
# Template setup
# ----------------------------
templates = Jinja2Templates(directory="templates")

# ----------------------------
# Alias validation
# ----------------------------
app = FastAPI(title="URL Shortener (FastAPI + Upstash Redis)", debug=True)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent.absolute() / "static"),
    name="static",
)

# ----------------------------
# Alias validation
# ----------------------------
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,100}$")

def valid_alias(alias: str) -> bool:
    return bool(ALIAS_RE.fullmatch(alias))

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

# ----------------------------
# TTL conversion
# ----------------------------
def format_ttl(ttl: int) -> str:
    if ttl == 0:
        return "as long as you want"
    days = ttl // 86400
    return f"{days} day{'s' if days != 1 else ''}"


# ----------------------------
# Rate limiter (10 req/min)
# ----------------------------
def check_rate_limit(client_id: str, limit: int = 10, period_seconds: int = 60):
    key = f"rate:{client_id}"
    try:
        # Increment request count
        count = redis_client.incr(key)
        # Set expiry window if new
        if count == 1:
            redis_client.expire(key, period_seconds)
        # Check limit
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: Only {limit} requests allowed per {period_seconds} seconds."
            )
    except Exception as e:
        print(f"[RateLimit Error] {e}")


# ----------------------------
# Homepage and other pages
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "short_url": None, "error": None})
@app.get('/pricing')
def pricing(request:Request):
    return templates.TemplateResponse("pricing.html",{"request": request, "short_url": None, "error": None})
@app.get('/about')
def about(request:Request):
    return templates.TemplateResponse("about.html",{"request": request, "short_url": None, "error": None})

# ----------------------------
# POST /shorten
# ----------------------------
@app.post("/shorten", response_class=HTMLResponse)
async def shorten_url(
    request: Request,
    original_url: str = Form(...),
    custom_alias: Optional[str] = Form(None),
    ttl: int = Form(...)
):
    client_id = get_client_id(request)
    check_rate_limit(client_id, limit=10, period_seconds=60)

    # Normalize URL
    if not original_url.startswith(("http://", "https://")):
        original_url = "http://" + original_url
    long_url = original_url.strip()
    created_at = datetime.utcnow().isoformat()

    # Custom alias handling
    if custom_alias:
        custom_alias = custom_alias.strip()
        if not valid_alias(custom_alias):
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "short_url": None, "error": "Invalid alias (A-Z, a-z, 0-9, _ or - only)."}
            )
        ok = redis_client.set(f"url:{custom_alias}", long_url, nx=True, ex=ttl)
        if not ok:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "short_url": None, "error": "Alias already in use."}
            )
        short_code = custom_alias
    else:
        # Generate random code
        alphabet = string.ascii_letters + string.digits
        while True:
            short_code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not redis_client.exists(f"url:{short_code}"):
                break
        redis_client.set(f"url:{short_code}", long_url, ex=ttl)

    # Metadata
    redis_client.hmset(
        f"meta:{short_code}",
        {"created_at": created_at, "owner": client_id, "ttl": ttl}
    )
    redis_client.expire(f"meta:{short_code}", ttl)

    # Click counter
    redis_client.set(f"clicks:{short_code}", 0, ex=ttl)

    readable_ttl = format_ttl(ttl)
    short_url = str(request.base_url).rstrip("/") + "/" + short_code

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "short_url": short_url, "error": None, "readable_ttl": readable_ttl}
    )

# ----------------------------
# Redirect short code
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
    return {
        "short_code": short_code,
        "long_url": long_url,
        "clicks": int(clicks),
        "meta": meta
    }

# Analytics page
@app.get("/analytics/{code}", response_class=HTMLResponse)
def analytics_page(request: Request, code: str):
    meta = redis_client.hgetall(f"meta:{code}") or {}
    clicks = redis_client.get(f"clicks:{code}") or 0
    return templates.TemplateResponse("analytics.html", {"request": request, "code": code, "meta": meta, "clicks": int(clicks)})