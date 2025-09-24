# app/utils/urls.py
from __future__ import annotations
from urllib.parse import urlencode
from starlette.requests import Request

def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())

def build_public_form_url(request: Request, machine_type: str, machine_serial: str, lang: str | None = None) -> str:
    """
    Build an absolute URL to the public form with prefilled fields.
    Example: http://127.0.0.1:8000/public/form?machine_type=MTC-45&machine_serial=SN-123&lang=en
    """
    base = str(request.base_url).rstrip("/")           # e.g., http://127.0.0.1:8000
    path = "/public/form"                              # your existing public route
    params = {
        "machine_type": _norm(machine_type),
        "machine_serial": _norm(machine_serial),
    }
    if lang in ("en", "fr"):
        params["lang"] = lang

    return f"{base}{path}?{urlencode(params)}"
