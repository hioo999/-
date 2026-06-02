"""Lightweight dashboard APIs for the home page."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import UserAccount
from services.dashboard_service import get_dashboard_overview


router = APIRouter(prefix="/api/dashboard", tags=["首页 Dashboard"])


@router.get("/overview", summary="查询首页轻量概览")
async def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    return {"code": 0, "data": get_dashboard_overview(db, current_user)}
