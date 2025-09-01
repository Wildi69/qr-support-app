from typing import List, Dict, Optional

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

public_router = APIRouter(tags=["public"])

# Jinja2 template engine (path is from project root)
templates = Jinja2Templates(directory="app/templates")


@public_router.get("/ping")
def ping():
    return {"pong": True}


@public_router.get("/form")
def show_form(request: Request):
    # Render empty form (messages list optional)
    return templates.TemplateResponse("form.html", {"request": request, "messages": []})


@public_router.post("/form")
def submit_form(
    request: Request,
    machine_serial: str = Form(""),
    machine_type: str = Form(""),
    operator_name: str = Form(""),
    operator_phone: str = Form(""),
    summary: str = Form(""),
    website: str = Form(""),  # honeypot; must be empty
    db: Session = Depends(get_db),
):
    """
    Basic validation + DB insert:
    - required: operator_name, operator_phone, summary
    - summary <= 255 chars
    - honeypot 'website' must be empty
    - optional machine_serial/type: link ticket to an existing machine or create it
    """
    messages: List[Dict[str, str]] = []
    lang = request.query_params.get("lang", "en")

    # --- Validation ---
    if website.strip():
        messages.append(
            {"level": "error", "text": "Bot submission blocked." if lang == "en" else "Soumission automatisée bloquée."}
        )
    if not operator_name.strip():
        messages.append(
            {"level": "error", "text": "Name is required." if lang == "en" else "Le nom est requis."}
        )
    if not operator_phone.strip():
        messages.append(
            {"level": "error", "text": "Phone number is required." if lang == "en" else "Le numéro de téléphone est requis."}
        )
    if not summary.strip():
        messages.append(
            {"level": "error", "text": "Issue summary is required." if lang == "en" else "Le résumé du problème est requis."}
        )
    if len(summary) > 255:
        messages.append(
            {"level": "error", "text": "Issue summary must be 255 characters or less." if lang == "en" else "Le résumé doit contenir 255 caractères ou moins."}
        )

    if messages:
        # Re-render with errors and preserve user input
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "messages": messages,
                "machine_serial": machine_serial,
                "machine_type": machine_type,
                "operator_name": operator_name,
                "operator_phone": operator_phone,
                "summary": summary,
            },
            status_code=400,
        )

    # --- Find-or-create Machine (optional) ---
    machine_id: Optional[int] = None
    if machine_serial.strip() and machine_type.strip():
        existing = (
            db.query(models.Machine)
            .filter(models.Machine.serial == machine_serial.strip())
            .one_or_none()
        )
        if existing:
            machine = existing
        else:
            machine = models.Machine(serial=machine_serial.strip(), type=machine_type.strip())
            db.add(machine)
            db.flush()  # get machine.id without full commit
        machine_id = machine.id

    # --- Create Ticket ---
    ticket = models.Ticket(
        machine_id=machine_id,
        operator_name=operator_name.strip(),
        operator_phone=operator_phone.strip(),
        summary=summary.strip(),
        status=models.TicketStatus.new,
    )
    db.add(ticket)
    db.flush()  # ensure ticket.id is available

    # --- Audit event (link directly to the new ticket) ---
    audit = models.AuditEvent(
        actor="public:operator",
        action="ticket.create",
        entity_type="ticket",
        entity_id=ticket.id,  # <-- set here, no raw SQL
        meta={
            "machine_serial": machine_serial.strip() or None,
            "machine_type": machine_type.strip() or None,
        },
    )
    db.add(audit)

    db.commit()

    # --- Success response ---
    messages.append(
        {"level": "success", "text": "Ticket submitted. Thank you!" if lang == "en" else "Billet soumis. Merci!"}
    )
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "messages": messages,
            "machine_serial": machine_serial,  # keep these visible for operator
            "machine_type": machine_type,
            # Clear operator fields after success
            "operator_name": "",
            "operator_phone": "",
            "summary": "",
        },
        status_code=201,
    )
