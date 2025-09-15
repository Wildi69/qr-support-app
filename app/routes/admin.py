# app/routes/admin.py
from typing import Optional, Dict, Any

import bcrypt
import hmac
import hashlib
import secrets
import time

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    status,
    Response,
    HTTPException,
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.utils import settings
from app.utils import session as sess
from app.utils import csrf as csrf_utils
from app.utils import rate_limit, flash

# --- Templates ---
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["admin"])

# --- Optional DB/Audit (soft-fail if schema differs) ---
try:
    from app.database import get_db
    from app.models import AuditEvent
except Exception:  # pragma: no cover
    get_db = None
    AuditEvent = None  # type: ignore


def _audit_safe(request: Request, kind: str, actor: str = "", note: str = "") -> None:
    """Try to write an AuditEvent; ignore if model/schema differs."""
    if not get_db or not AuditEvent:
        return
    try:
        db = next(get_db())
        ip = request.client.host if request.client else ""
        evt = AuditEvent(event_type=kind, actor=actor or ip, note=note)
        db.add(evt)
        db.commit()
    except Exception:
        # Silent fail; we’ll refine once models are finalized
        pass


# ---------------------------
# Pre-login CSRF (separate cookie)
# ---------------------------
_PRELOGIN_COOKIE = "qr_prelogin_csrf"
_PRELOGIN_TTL_S = 600  # 10 minutes


def _sign(msg: bytes) -> bytes:
    return hmac.new(settings.SESSION_SECRET.encode(), msg, hashlib.sha256).digest()


def _issue_prelogin_csrf() -> str:
    payload = {"t": int(time.time()), "n": secrets.token_urlsafe(32)}
    raw = f"{payload['t']}.{payload['n']}".encode()
    sig = _sign(raw)
    return f"{payload['t']}.{payload['n']}.{sig.hex()}"


def _verify_prelogin_csrf(cookie_val: Optional[str], form_val: Optional[str]) -> bool:
    if not cookie_val or not form_val:
        return False
    try:
        t_s, nonce, hexsig = cookie_val.split(".", 2)
        raw = f"{t_s}.{nonce}".encode()
        good = hmac.compare_digest(_sign(raw).hex(), hexsig)
        fresh = (int(time.time()) - int(t_s)) <= _PRELOGIN_TTL_S
        return good and fresh and hmac.compare_digest(nonce, form_val)
    except Exception:
        return False


# ---------------------------
# Guard (require_admin)
# ---------------------------
def require_admin(request: Request) -> Dict[str, Any]:
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    payload = sess.verify_session(cookie)  # dict on success, falsy on failure
    if not payload:
        # Dependencies must raise exceptions, not return Response objects
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return payload


# ---------------------------
# Routes
# ---------------------------
@router.get("/login")
def get_login(request: Request) -> Response:
    """
    Render login page; ensure a pre-login CSRF cookie exists so the login POST can be protected.
    Also display any flash messages (and clear the cookie) in this response.
    """
    # 1) Pre-login CSRF
    token = _issue_prelogin_csrf()

    # 2) Read flash messages from the incoming request cookie first
    flash_cookie = request.cookies.get(settings.FLASH_COOKIE_NAME)
    from app.utils import flash as flash_mod  # local alias, safe helper
    msgs = flash_mod._decode(flash_cookie) if flash_cookie else []  # returns [] on bad/missing

    # 3) Build the response with messages already in the context
    response = templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "prelogin_csrf": token.split(".")[1],  # only the nonce goes in the form
            "messages": msgs,
        },
    )

    # 4) Set new pre-login CSRF cookie for the upcoming POST
    response.set_cookie(
        key=_PRELOGIN_COOKIE,
        value=token,
        max_age=_PRELOGIN_TTL_S,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    # 5) Clear flash cookie now that we've rendered it
    if flash_cookie:
        response.delete_cookie(settings.FLASH_COOKIE_NAME, path="/")

    return response


@router.post("/login")
async def post_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: Optional[str] = Form(None, alias="_csrf"),
) -> Response:
    # Rate limit check
    ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limit.check(ip)
    if not allowed:
        resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        flash.add(resp, "error", "too_many_attempts")
        _audit_safe(request, "admin.login.lockout", actor=username, note=f"retry_after={retry_after}")
        return resp

    # Validate pre-login CSRF (cookie vs form)
    if not _verify_prelogin_csrf(request.cookies.get(_PRELOGIN_COOKIE), csrf_token):
        resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        flash.add(resp, "error", "invalid_session")
        _audit_safe(request, "admin.login.failure", actor=username, note="csrf")
        return resp

    # Credential check (generic error on failure)
    if username.strip().lower() != settings.ADMIN_USER.strip().lower():
        rate_limit.record_failure(ip)
        resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        flash.add(resp, "error", "invalid_credentials")
        _audit_safe(request, "admin.login.failure", actor=username, note="user")
        return resp

    try:
        ok = bcrypt.checkpw(password.encode(), settings.ADMIN_PASS_HASH.encode())
    except Exception:
        ok = False

    if not ok:
        rate_limit.record_failure(ip)
        resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        flash.add(resp, "error", "invalid_credentials")
        _audit_safe(request, "admin.login.failure", actor=username, note="password")
        return resp

    # Success → clear limiter and issue session
    rate_limit.record_success(ip)
    cookie_val = sess.issue_session(admin_id=username)
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(value=cookie_val, **sess.cookie_params())

    # Clear pre-login CSRF cookie
    resp.delete_cookie(_PRELOGIN_COOKIE, path="/")
    _audit_safe(request, "admin.login.success", actor=username)
    return resp


@router.post("/logout")
async def post_logout(request: Request) -> Response:
    form = await request.form()
    _csrf = form.get("_csrf")
    try:
        csrf_utils.require_csrf(request, _csrf)
    except Exception:
        resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        flash.add(resp, "error", "invalid_request")
        return resp

    resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    # Clear session
    params = sess.clear_cookie_params()
    resp.delete_cookie(key=params["key"], path=params["path"])
    _audit_safe(request, "admin.logout", actor="admin")
    return resp


@router.get("")
def admin_home(request: Request, payload: Dict[str, Any] = Depends(require_admin)) -> Response:
    """
    Minimal landing page so redirects have a valid target.
    """
    response = templates.TemplateResponse(
        "admin/base.html",
        {
            "request": request,
            "title": "Admin Dashboard",
            "payload": payload,
            "messages": [],  # filled after consume()
        },
    )
    msgs = flash.consume(request, response)
    response.context.update({"messages": msgs})
    return response
