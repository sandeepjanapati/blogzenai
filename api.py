import base64
import hashlib
import hmac
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator

from main import run_blog_agent
from utils.database import (
    get_anonymous_generation_usage,
    get_history,
    get_history_item_by_id,
    mark_anonymous_generation_used,
    release_anonymous_generation_reservation,
    reserve_anonymous_generation,
    save_generation_to_history,
    save_user_generation_to_history,
)
from utils.runtime_config import get_runtime_value, is_local_hostname

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

DEFAULT_ALLOWED_ORIGINS = [
    "https://bolgzenai.web.app",
    "https://bolgzenai.firebaseapp.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
ANON_COOKIE_NAME = "blogzenai_anon_usage"
ANON_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
ANON_RESERVATION_TTL = timedelta(minutes=15)


def build_allowed_origins():
    configured_origins = get_runtime_value("ALLOWED_ORIGINS", allow_local_dev_default=False)
    if not configured_origins:
        return DEFAULT_ALLOWED_ORIGINS
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


def app_error(status_code: int, detail: Any, code: str):
    return HTTPException(status_code=status_code, detail={"detail": detail, "code": code})


def default_error_code(status_code: int):
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
    }.get(status_code, "HTTP_ERROR")


def normalize_http_error_payload(exc: HTTPException):
    if isinstance(exc.detail, dict):
        payload = dict(exc.detail)
        payload.setdefault("code", default_error_code(exc.status_code))
        if "detail" not in payload:
            payload["detail"] = "Request failed."
        return payload
    return {"detail": exc.detail, "code": default_error_code(exc.status_code)}


def get_anon_cookie_secret():
    secret = get_runtime_value("ANON_COOKIE_SECRET")
    if not secret:
        raise app_error(
            500,
            "Anonymous generation is not configured on the server.",
            "ANON_COOKIE_NOT_CONFIGURED",
        )
    return secret.encode("utf-8")


def encode_cookie_signature(cookie_id: str, secret: bytes):
    digest = hmac.new(secret, cookie_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_anonymous_cookie(cookie_id: str, secret: bytes):
    return f"{cookie_id}.{encode_cookie_signature(cookie_id, secret)}"


def verify_anonymous_cookie(cookie_value: str | None, secret: bytes):
    if not cookie_value or "." not in cookie_value:
        return None

    cookie_id, provided_signature = cookie_value.rsplit(".", 1)
    if not cookie_id or not provided_signature:
        return None

    expected_signature = encode_cookie_signature(cookie_id, secret)
    if hmac.compare_digest(provided_signature, expected_signature):
        return cookie_id
    return None


def is_stale_reservation(usage: dict):
    reserved_at = usage.get("reservedAt")
    if not isinstance(reserved_at, datetime):
        return False
    return reserved_at <= datetime.now(timezone.utc) - ANON_RESERVATION_TTL


class BlogRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=160)
    tone: Literal["informative", "educational", "creative", "formal", "technical"] = "informative"

    @field_validator("topic", mode="before")
    @classmethod
    def trim_topic(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.info("Application startup: initializing Firebase Admin SDK.")
    try:
        firebase_creds_json = get_runtime_value("FIREBASE_CREDENTIALS_JSON", allow_local_dev_default=False)
        if firebase_creds_json:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                LOGGER.info("Firebase Admin SDK initialized successfully.")
        else:
            LOGGER.error("FIREBASE_CREDENTIALS_JSON could not be resolved.")

        if not get_runtime_value("ANON_COOKIE_SECRET"):
            LOGGER.error("ANON_COOKIE_SECRET could not be resolved. Anonymous free generation is disabled.")
    except Exception as exc:
        LOGGER.error("Firebase Admin SDK init failed: %s", exc, exc_info=True)

    yield
    LOGGER.info("Application shutdown.")


app = FastAPI(title="BlogZenAI API", version="1.1.0", lifespan=lifespan)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=build_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=normalize_http_error_payload(exc),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    LOGGER.error("Unhandled application error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "code": "INTERNAL_SERVER_ERROR"},
    )


async def get_current_user(token: str | None = Depends(oauth2_scheme)):
    if not token:
        raise app_error(401, "Authentication required.", "AUTH_REQUIRED")
    if not firebase_admin._apps:
        raise app_error(500, "Auth service not configured on the server.", "AUTH_NOT_CONFIGURED")

    try:
        return auth.verify_id_token(token, check_revoked=True)
    except Exception as exc:
        LOGGER.error("Token verification failed: %s", exc)
        raise app_error(401, "Invalid auth credentials.", "INVALID_AUTH_CREDENTIALS")


async def generate_blog_payload(request: BlogRequest):
    markdown_content, metadata = await run_blog_agent(
        request.topic, request.tone, "/tmp/output", run_mode="api"
    )
    if not markdown_content or not metadata:
        raise app_error(500, "Failed to generate content.", "GENERATION_FAILED")
    return markdown_content, metadata


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "firebase_initialized": bool(firebase_admin._apps),
        "anonymous_generation_configured": bool(get_runtime_value("ANON_COOKIE_SECRET")),
        "project_id": get_runtime_value("GCP_PROJECT", allow_local_dev_default=False),
    }


@app.post("/generate-blog-free")
async def generate_blog_free_endpoint(request: BlogRequest, http_request: Request):
    LOGGER.info("Anonymous generation request for topic: %s", request.topic)
    secret = get_anon_cookie_secret()

    signed_cookie = http_request.cookies.get(ANON_COOKIE_NAME)
    cookie_id = verify_anonymous_cookie(signed_cookie, secret)
    if not cookie_id:
        cookie_id = secrets.token_urlsafe(32)

    usage = get_anonymous_generation_usage(cookie_id)
    if usage and usage.get("status") == "reserved" and is_stale_reservation(usage):
        release_anonymous_generation_reservation(cookie_id)
        usage = None

    if usage and usage.get("status") == "used":
        raise app_error(
            403,
            "Your anonymous free generation has already been used. Sign in to continue.",
            "FREE_TRY_USED",
        )

    if usage and usage.get("status") == "reserved":
        raise app_error(
            409,
            "A free generation is already in progress for this browser.",
            "FREE_TRY_IN_PROGRESS",
        )

    if not reserve_anonymous_generation(cookie_id):
        usage = get_anonymous_generation_usage(cookie_id)
        if usage and usage.get("status") == "used":
            raise app_error(
                403,
                "Your anonymous free generation has already been used. Sign in to continue.",
                "FREE_TRY_USED",
            )
        raise app_error(
            409,
            "A free generation is already in progress for this browser.",
            "FREE_TRY_IN_PROGRESS",
        )

    try:
        markdown_content, metadata = await generate_blog_payload(request)
        history_id = save_generation_to_history(
            request.topic, request.tone, metadata, markdown_content
        )
        mark_anonymous_generation_used(cookie_id, history_id)

        response = JSONResponse(
            {
                "status": "success",
                "history_id": history_id,
                "topic": request.topic,
                "metadata": metadata,
                "blog_content_markdown": markdown_content,
            }
        )
        cookie_is_local = is_local_hostname(http_request.url.hostname)
        response.set_cookie(
            key=ANON_COOKIE_NAME,
            value=sign_anonymous_cookie(cookie_id, secret),
            max_age=ANON_COOKIE_MAX_AGE,
            httponly=True,
            secure=not cookie_is_local,
            samesite="lax" if cookie_is_local else "none",
            path="/",
        )
        return response
    except HTTPException:
        release_anonymous_generation_reservation(cookie_id)
        raise
    except Exception:
        release_anonymous_generation_reservation(cookie_id)
        raise


@app.post("/generate-blog")
async def generate_blog_endpoint(request: BlogRequest, user: dict = Depends(get_current_user)):
    LOGGER.info("Authenticated request from user: %s", user.get("uid"))
    markdown_content, metadata = await generate_blog_payload(request)
    user_info = {
        "uid": user.get("uid"),
        "name": user.get("name"),
        "email": user.get("email"),
    }
    history_id = save_user_generation_to_history(
        user_info, request.topic, request.tone, metadata, markdown_content
    )
    return {
        "status": "success",
        "history_id": history_id,
        "topic": request.topic,
        "metadata": metadata,
        "blog_content_markdown": markdown_content,
    }


@app.get("/history")
async def get_history_list_endpoint(
    user: dict = Depends(get_current_user), limit: int = Query(20, gt=0, le=100)
):
    return get_history(user_id=user["uid"], limit=limit)


@app.get("/history/{history_id}")
async def get_single_history_item_endpoint(
    history_id: str, user: dict = Depends(get_current_user)
):
    history_item = get_history_item_by_id(history_id)
    if history_item is None or history_item.get("userId") != user["uid"]:
        raise app_error(
            404,
            "History item not found or you do not have permission.",
            "HISTORY_ITEM_NOT_FOUND",
        )
    return history_item
