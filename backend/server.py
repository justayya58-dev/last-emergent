import hmac
from datetime import datetime, timedelta, timezone

import jwt
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from routers.auditpro import router as auditpro_router


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not accept API traffic until correctness-critical indexes are ready.
    await ensure_indexes()
    yield
    client.close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

AUTH_COOKIE = "auditpro_session"
AUTH_ALGORITHM = "HS256"
AUTH_PATHS = {"/api/auth/login", "/api/auth/logout", "/api/auth/me"}


def auth_config() -> tuple[str, str, str]:
    username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
    password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
    secret = os.environ.get("AUDITPRO_SESSION_SECRET", "")
    if len(password) < 16 or len(secret) < 32:
        raise RuntimeError(
            "Set AUDITPRO_ADMIN_PASSWORD (min 16 chars) and AUDITPRO_SESSION_SECRET (min 32 chars)."
        )
    return username, password, secret


@api_router.post("/auth/login")
async def auth_login(request: Request):
    try:
        username, password, secret = auth_config()
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    supplied_user = str(payload.get("username", ""))
    supplied_password = str(payload.get("password", ""))
    if not (
        hmac.compare_digest(supplied_user.encode(), username.encode())
        and hmac.compare_digest(supplied_password.encode(), password.encode())
    ):
        return JSONResponse(status_code=401, content={"detail": "Username atau password salah."})
    token = jwt.encode(
        {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        secret,
        algorithm=AUTH_ALGORITHM,
    )
    result = JSONResponse(content={"authenticated": True, "username": username})
    result.set_cookie(
        AUTH_COOKIE, token, httponly=True, secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict", max_age=8 * 60 * 60, path="/",
    )
    return result


@api_router.post("/auth/logout")
async def auth_logout():
    result = JSONResponse(content={"authenticated": False})
    result.delete_cookie(AUTH_COOKIE, path="/", httponly=True, samesite="strict")
    return result


@api_router.get("/auth/me")
async def auth_me(request: Request):
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Autentikasi diperlukan."})
    try:
        _, _, secret = auth_config()
        payload = jwt.decode(token, secret, algorithms=[AUTH_ALGORITHM])
        return {"authenticated": True, "username": payload["sub"]}
    except (jwt.InvalidTokenError, RuntimeError, KeyError):
        return JSONResponse(status_code=401, content={"detail": "Sesi tidak valid atau kedaluwarsa."})


@app.middleware("http")
async def require_api_auth(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path not in AUTH_PATHS and request.method != "OPTIONS":
        token = request.cookies.get(AUTH_COOKIE)
        try:
            _, _, secret = auth_config()
            if not token:
                raise jwt.InvalidTokenError("missing session")
            jwt.decode(token, secret, algorithms=[AUTH_ALGORITHM])
        except (jwt.InvalidTokenError, RuntimeError):
            return JSONResponse(status_code=401, content={"detail": "Sesi tidak valid atau kedaluwarsa."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
if not cors_origins or "*" in cors_origins:
    raise RuntimeError("CORS_ORIGINS harus berisi origin eksplisit; wildcard tidak diizinkan.")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Include all API routes last so every endpoint remains under /api.
api_router.include_router(auditpro_router)
app.include_router(api_router)
