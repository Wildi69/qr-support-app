from fastapi import APIRouter, Request          # ← add Request
from fastapi.templating import Jinja2Templates  # ← add this

public_router = APIRouter(tags=["public"])

# Jinja2 template engine (path is from project root)
templates = Jinja2Templates(directory="app/templates")

@public_router.get("/ping")
def ping():
    return {"pong": True}

@public_router.get("/form")
def show_form(request: Request):
    # messages is optional; empty list for now
    return templates.TemplateResponse("form.html", {"request": request, "messages": []})
