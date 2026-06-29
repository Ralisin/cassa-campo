from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.routers import (
    auth,
    casse,
    dashboard,
    exports,
    movements,
    notifications,
    receipts,
    reimbursements,
    settings as settings_router,
    system,
    transfers,
    users,
)
from app.system_admin import ensure_system_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        ensure_system_admin(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(movements.router)
app.include_router(notifications.router)
app.include_router(receipts.router)
app.include_router(settings_router.router)
app.include_router(exports.router)
app.include_router(users.router)
app.include_router(reimbursements.router)
app.include_router(transfers.router)
app.include_router(casse.router)
app.include_router(system.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
