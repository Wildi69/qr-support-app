# app/utils/session.py
# Signed-cookie session: payload.sign with HMAC-SHA256 (base64url without padding).
import base64
import hashlib
import hmac
import json
import time
import secrets

from typing import Optional, Tuple, Dict, Any
from . import settings

_B64ALT = b"-_"

def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode())

def _sign(msg: bytes) -> bytes:
    return hmac.new(settings.SESSION_SECRET.encode(), msg, hashlib.sha256).digest()

def _ct_eq(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)

def _now() -> int:
    return int(time.time())

def _max_age_s() -> int:
    return settings.SESSION_MAX_AGE_MIN * 60

def issue_session(admin_id: str) -> str:
    payload = {
        "admin_id": admin_id,
        "csrf": secrets.token_urlsafe(32),
        "issued_at": _now(),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = _sign(raw)
    return f"{_b64url_nopad(raw)}.{_b64url_nopad(sig)}"

def verify_session(cookie_value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cookie_value or "." not in cookie_value:
        return None
    p_b64, s_b64 = cookie_value.split(".", 1)
    try:
        raw = _b64url_decode(p_b64)
        sig = _b64url_decode(s_b64)
    except Exception:
        return None
    if not _ct_eq(_sign(raw), sig):
        return None
    try:
        payload = json.loads(raw.decode())
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    issued = int(payload.get("issued_at", 0))
    if _now() > issued + _max_age_s():
        return None
    # minimal shape check
    if not payload.get("admin_id") or not payload.get("csrf"):
        return None
    return payload

def encode_cookie(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = _sign(raw)
    return f"{_b64url_nopad(raw)}.{_b64url_nopad(sig)}"

def rotate_csrf(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    payload = dict(payload)
    payload["csrf"] = secrets.token_urlsafe(32)
    payload["issued_at"] = _now()  # refresh issue time on rotation
    return payload, encode_cookie(payload)

def cookie_params() -> Dict[str, Any]:
    return {
        "key": settings.SESSION_COOKIE_NAME,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": _max_age_s(),
        "path": "/",
    }

def clear_cookie_params() -> Dict[str, Any]:
    return {
        "key": settings.SESSION_COOKIE_NAME,
        "max_age": 0,
        "path": "/",
    }
