# app/utils/settings.py
# Centralized, strict .env access (English comments; UI bilingual comes later in templates).
import os

def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v

# Required
ADMIN_USER = _req("ADMIN_USER")
ADMIN_PASS_HASH = _req("ADMIN_PASS_HASH")
SESSION_SECRET = _req("SESSION_SECRET")

# Optional with defaults
def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y")

def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None else default

SESSION_MAX_AGE_MIN = _get_int("SESSION_MAX_AGE_MIN", 60 * 24 * 14)  # default 14 days
COOKIE_SECURE = _get_bool("COOKIE_SECURE", True)
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_NAME = "qr_admin_session"
FLASH_COOKIE_NAME = "qr_flash"
