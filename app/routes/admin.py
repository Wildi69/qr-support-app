from fastapi import APIRouter

# Note: we’ll add real auth/rate-limit later; this is just the scaffold.
admin_router = APIRouter(tags=["admin"])

@admin_router.get("/ping")
def ping_admin():
    return {"pong": True, "scope": "admin"}
