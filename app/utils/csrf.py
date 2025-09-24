# app/utils/csrf.py
from fastapi import Request, HTTPException, status
import hmac
from typing import Optional
from .session import verify_session
from . import settings  # <-- add

def get_csrf_from_request(request: Request) -> str:
    cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)  # <-- use setting
    payload = verify_session(cookie_val)
    return payload["csrf"] if payload else ""

def require_csrf(request: Request, form_value: Optional[str]) -> None:
    if not form_value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")
    cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)  # <-- use setting
    payload = verify_session(cookie_val)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session")
    if not hmac.compare_digest(payload["csrf"], form_value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
