from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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
    transfers,
    users,
)

app = FastAPI(title=settings.app_name)
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


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
