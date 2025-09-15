# ruff: noqa: E402
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root BEFORE importing anything that reads env vars
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from app.routes.public import public_router
from app.routes import admin as admin_routes

app = FastAPI()

# Routers
app.include_router(public_router, prefix="/public")
app.include_router(admin_routes.router)

# Simple health endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Hello World"}
