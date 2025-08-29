from fastapi import FastAPI
from app.routes.public import public_router
from app.routes.admin import admin_router

app = FastAPI()

app.include_router(public_router, prefix="/public")
app.include_router(admin_router, prefix="/admin")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Hello World"}
