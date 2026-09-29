from fastapi import APIRouter

from app.api.v1.routes import auth, finance, planning, platform, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users, planning, finance, platform):
    api_router.include_router(module.router)
