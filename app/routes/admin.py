# app/routes/admin.py
from typing import Optional, Dict, Any

import bcrypt
import hmac
import hashlib
import secrets
import time
import io
import base64
import re
import qrcode

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

from app.utils.urls import build_public_form_url
from app.utils import settings
from app.utils import session as sess
from app.utils import csrf as csrf_utils
from app.utils import rate_limit, flash

# --- Templates ---
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = csrf_utils.get_csrf_from_request

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


# ---------------------------
# Dashboard (protected)
# ---------------------------
@router.get("", name="admin_dashboard")
def admin_dashboard(request: Request, payload: Dict[str, Any] = Depends(require_admin)) -> Response:
    """
    Admin landing page (dashboard). Requires a valid admin session.
    """
    response = templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "Admin Dashboard",
            "admin_user": settings.ADMIN_USER,
            "payload": payload,
            "messages": [],  # filled after consume()
        },
    )
    msgs = flash.consume(request, response)
    response.context.update({"messages": msgs})
    return response


# ---------------------------
# QR Generator (protected)
# ---------------------------
@router.get("/qr", name="admin_qr_form")
def admin_qr_form(request: Request, payload: Dict[str, Any] = Depends(require_admin)) -> Response:
    """
    Render the QR Generator form.
    """
    response = templates.TemplateResponse(
        "admin/qr_generator.html",
        {
            "request": request,
            "title": "QR Generator",
            "payload": payload,
            "messages": [],
        },
    )
    msgs = flash.consume(request, response)
    response.context.update({"messages": msgs})
    _audit_safe(request, "admin.qr.view")
    return response


@router.post("/qr", name="admin_qr_submit")
async def admin_qr_submit(
    request: Request,
    machine_type: str = Form(...),
    serial: str = Form(...),
    csrf_token: str = Form(..., alias="_csrf"),
    payload: Dict[str, Any] = Depends(require_admin),
) -> Response:
    """
    Validate CSRF + inputs, then build the public URL + QR PNG (base64) and
    re-render the form showing both.
    """
    # CSRF
    try:
        csrf_utils.require_csrf(request, csrf_token)
    except Exception:
        resp = templates.TemplateResponse(
            "admin/qr_generator.html",
            {
                "request": request,
                "title": "QR Generator",
                "payload": payload,
                "messages": [{"level": "error", "code": "invalid_request"}],
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        return resp

    # Basic normalization/validation (MVP)
    mt = (machine_type or "").strip()
    sn = (serial or "").strip()
    if not mt or not sn:
        return templates.TemplateResponse(
            "admin/qr_generator.html",
            {
                "request": request,
                "title": "QR Generator",
                "payload": payload,
                "messages": [{"level": "error", "code": "missing_fields"}],
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if len(mt) > 64 or len(sn) > 64:
        return templates.TemplateResponse(
            "admin/qr_generator.html",
            {
                "request": request,
                "title": "QR Generator",
                "payload": payload,
                "messages": [{"level": "error", "code": "input_too_long"}],
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Build absolute public URL to prefill the public form
    lang = request.query_params.get("lang")
    public_url = build_public_form_url(request, mt, sn, lang)

    # Generate QR PNG in-memory and base64-encode it
    qr = qrcode.QRCode(
        version=None,  # automatic
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # medium (~15% recovery)
        box_size=10,  # pixel size of each "box"
        border=2,     # quiet zone (2-4 typical)
    )
    qr.add_data(public_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    # Build a safe download filename, e.g., MTC-45_1234.png
    def _slug(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip()).strip("_")

    download_filename = f"{_slug(mt)}_{_slug(sn)}.png"

    _audit_safe(request, "admin.qr.generated", note=f"machine_type={mt}, serial={sn}")

    return templates.TemplateResponse(
        "admin/qr_generator.html",
        {
            "request": request,
            "title": "QR Generator",
            "payload": payload,
            "public_url": public_url,
            "qr_png_b64": qr_png_b64,
            "machine_type": mt,
            "serial": sn,
            "download_filename": download_filename,
            "messages": [{"level": "success", "code": "qr_generated"}],
        },
    )
