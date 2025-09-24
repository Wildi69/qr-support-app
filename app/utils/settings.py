from __future__ import annotations

import os
from pathlib import Path

# --- Locate project root and .env ---
# utils/settings.py → parents = [utils, app, <ROOT>]
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"


# --- Load environment variables ---
def _load_env() -> None:
    """
    Load environment variables from .env if possible.
    1. Try python-dotenv if available.
    2. Fallback: tiny manual parser.
    """
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore

        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH, override=False)
        else:
            # Try auto-discovery from current working directory
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path, override=False)
    except Exception:
        # Fallback manual parser
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


# --- Helper to fetch env vars ---
def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    """
    Read environment variable, with optional default or required flag.
    """
    val = os.getenv(name, default)
    if required and (val is None or val.strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val or ""


# --- Application settings ---
ADMIN_USER: str = _env("ADMIN_USER", required=True)
ADMIN_PASS_HASH: str = _env("ADMIN_PASS_HASH", required=True)
SECRET_KEY: str = _env("SECRET_KEY", required=True)

# Database
DATABASE_URL: str = _env("DATABASE_URL", "sqlite:///dev.db")

# Optional knobs with safe defaults
APP_TITLE: str = _env("APP_TITLE", "QR Support")
DEBUG: bool = _env("DEBUG", "false").lower() in {"1", "true", "yes", "y"}

# Cookie/security knobs
COOKIE_SECURE: bool = _env("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
COOKIE_SAMESITE: str = _env("COOKIE_SAMESITE", "lax")
SESSION_SECRET: str = _env("SESSION_SECRET", SECRET_KEY)  # fallback to SECRET_KEY
SESSION_COOKIE_NAME: str = _env("SESSION_COOKIE_NAME", "qr_session")
FLASH_COOKIE_NAME: str = _env("FLASH_COOKIE_NAME", "qr_flash")
SESSION_MAX_AGE_MIN: int = int(_env("SESSION_MAX_AGE_MIN", "60"))