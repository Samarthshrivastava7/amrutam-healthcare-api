import os

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
except ValueError as exc:
    raise RuntimeError(
        "ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer"
    ) from exc

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing from .env")

if "replace" in JWT_SECRET_KEY.lower() or "change-me" in JWT_SECRET_KEY.lower():
    raise RuntimeError(
        "JWT_SECRET_KEY is still a placeholder; configure a unique random secret"
    )

if len(JWT_SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")

if JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
    raise RuntimeError(
        "JWT_ALGORITHM must be one of HS256, HS384, or HS512 for HMAC signing"
    )

if ACCESS_TOKEN_EXPIRE_MINUTES < 1:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")
