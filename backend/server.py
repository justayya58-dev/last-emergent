import base64
import hmac
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime
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

# Basic authentication protects every API route except the harmless API root.
# Configure a strong AUDITPRO_ADMIN_PASSWORD before exposing the service.
@app.middleware("http")
async def require_api_auth(request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/":
        username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
        password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
        if len(password) < 16:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"detail": "Server auth belum dikonfigurasi; set AUDITPRO_ADMIN_PASSWORD minimal 16 karakter."},
            )
        authorization = request.headers.get("authorization", "")
        supplied_user = ""
        supplied_password = ""
        if authorization.startswith("Basic "):
            try:
                decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
                supplied_user, supplied_password = decoded.split(":", 1)
            except (ValueError, UnicodeDecodeError):
                pass
        valid_user = hmac.compare_digest(supplied_user.encode(), username.encode())
        valid_password = hmac.compare_digest(supplied_password.encode(), password.encode())
        if not (valid_user and valid_password):
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Autentikasi diperlukan."},
                headers={"WWW-Authenticate": 'Basic realm="AuditPro", charset="UTF-8"'},
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
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
