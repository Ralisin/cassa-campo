from fastapi import APIRouter

from app.dependencies import CurrentCassa, DbSession
from app.schemas import DashboardRead
from app.services import get_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(db: DbSession, cassa: CurrentCassa) -> DashboardRead:
    return get_dashboard(db, cassa.id)

