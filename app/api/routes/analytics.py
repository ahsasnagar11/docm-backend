# app/api/routes/analytics.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.user import User
from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stats")
def get_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return analytics_service.get_org_stats(db, current_user.org_id, days=days)


@router.get("/queries/over-time")
def get_query_volume(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return analytics_service.get_query_volume_over_time(db, current_user.org_id, days=days)


@router.get("/queries/top")
def get_top_questions(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return analytics_service.get_top_questions(db, current_user.org_id, limit=limit)


@router.get("/documents/stats")
def get_document_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return analytics_service.get_document_stats(db, current_user.org_id)
