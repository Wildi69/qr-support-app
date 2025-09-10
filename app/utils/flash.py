# app/utils/flash.py
# Signed, one-time flash messages via a separate cookie.
import base64
import hashlib
import hmac
import json

from typing import List, Dict, Any
from fastapi import Request, Response
from . import settings

def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode())

def _sign(msg: bytes) -> bytes:
    return hmac.new(settings.SESSION_SECRET.encode(), msg, hashlib.sha256).digest()

def _encode(messages: List[Dict[str, Any]]) -> str:
    raw = json.dumps(messages, separators=(",", ":"), sort_keys=True).encode()
    sig = _sign(raw)
    return f"{_b64url_nopad(raw)}.{_b64url_nopad(sig)}"

def _decode(cookie_val: str) -> List[Dict[str, Any]]:
    try:
        p_b64, s_b64 = cookie_val.split(".", 1)
        raw = _b64url_decode(p_b64)
        sig = _b64url_decode(s_b64)
        if not hmac.compare_digest(_sign(raw), sig):
            return []
        data = json.loads(raw.decode())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def add(response: Response, level: str, text: str) -> None:
    """
    level: 'success' | 'error' | 'info' | 'warning'
    """
    existing = []  # one-shot cookie; we always overwrite with a single message burst
    existing.append({"level": level, "text": text})
    response.set_cookie(
        key=settings.FLASH_COOKIE_NAME,
        value=_encode(existing),
        max_age=300,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

def consume(request: Request, response: Response) -> List[Dict[str, Any]]:
    val = request.cookies.get(settings.FLASH_COOKIE_NAME)
    msgs = _decode(val) if val else []
    if val:
        response.delete_cookie(settings.FLASH_COOKIE_NAME, path="/")
    return msgs

def _decode(cookie_val: str) -> List[Dict[str, Any]]:
    try:
        p_b64, s_b64 = cookie_val.split(".", 1)
        raw = _b64url_decode(p_b64)
        sig = _b64url_decode(s_b64)
        expected = _sign(raw)
        if not hmac.compare_digest(expected, sig):
            print("⚠️ Flash decode failed: signature mismatch")
            return []
        data = json.loads(raw.decode())
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ Flash decode error: {e}")
        return []

