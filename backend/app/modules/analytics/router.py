from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.analytics.schemas import DailyMetric,FunnelResponse,RetentionAnalytics
from app.modules.analytics.service import AnalyticsService
router=APIRouter(prefix="/admin/analytics",tags=["admin-analytics"])
def admin_user(user:UserEntity=Depends(require_roles(UserRole.ADMIN))): return user
@router.get("/daily",response_model=list[DailyMetric])
def daily(days:int=Query(30,ge=1,le=90),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AnalyticsService(db).daily(days)
@router.get("/funnel",response_model=FunnelResponse)
def funnel(days:int=Query(30,ge=1,le=90),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AnalyticsService(db).funnel(days)
@router.get("/retention",response_model=RetentionAnalytics)
def retention(days:int=Query(90,ge=1,le=90),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AnalyticsService(db).retention(days)
