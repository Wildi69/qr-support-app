# app/utils/csrf.py
# CSRF helpers to read token from the verified session and validate form posts.
from fastapi import Request, HTTPException, status
import hmac
from typing import Optional
from .session import verify_session

def get_csrf_from_request(request: Request) -> str:
    cookie_val = request.cookies.get("qr_admin_session")
    payload = verify_session(cookie_val)
    return payload["csrf"] if payload else ""

def require_csrf(request: Request, form_value: Optional[str]) -> None:
    if not form_value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")
    cookie_val = request.cookies.get("qr_admin_session")
    payload = verify_session(cookie_val)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session")
    if not hmac.compare_digest(payload["csrf"], form_value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
