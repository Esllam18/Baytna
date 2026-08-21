from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.admin_ops.schemas import *
from app.modules.admin_ops.service import AdminOperationsService

router=APIRouter(prefix="/admin",tags=["admin-operations"])
def admin_user(user:UserEntity=Depends(require_roles(UserRole.ADMIN))): return user

@router.get("/profile", response_model=AdminSelfProfile)
def profile(admin: UserEntity = Depends(admin_user)):
    return AdminSelfProfile(
        id=admin.id,
        phone=admin.phone,
        role=admin.role,
        is_active=admin.is_active,
    )

@router.get("/dashboard/overview",response_model=AdminDashboardOverview)
def overview(date_from:date|None=Query(None),date_to:date|None=Query(None),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).overview(date_from,date_to)

@router.get("/orders",response_model=list[AdminOrderListItem])
def orders(status:str|None=Query(None),chef_id:UUID|None=Query(None),customer_id:UUID|None=Query(None),date_from:date|None=Query(None),date_to:date|None=Query(None),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).list_orders(status=status,chef_id=chef_id,customer_id=customer_id,date_from=date_from,date_to=date_to,limit=limit,offset=offset)

@router.get("/orders/{order_id}",response_model=AdminOrderDetail)
def order_detail(order_id:UUID,_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).order_detail(order_id)

@router.post("/orders/{order_id}/notes",response_model=AdminOrderNoteResponse,status_code=201)
def add_note(order_id:UUID,payload:AdminOrderNoteCreate,request:Request,admin:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).add_note(order_id=order_id,admin_id=admin.id,note=payload.note,request_id=request.state.request_id)

@router.get("/orders/{order_id}/notes",response_model=list[AdminOrderNoteResponse])
def notes(order_id:UUID,_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).notes(order_id)

@router.get("/chefs",response_model=list[AdminChefListItem])
def chefs(status:str|None=Query(None),area:str|None=Query(None),verified:bool|None=Query(None),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).chefs(status=status,area=area,verified=verified,limit=limit,offset=offset)

@router.get("/chefs/{chef_id}",response_model=AdminChefDetail)
def chef_detail(chef_id:UUID,_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).chef_detail(chef_id)

@router.patch("/chefs/{chef_id}/status",response_model=AdminChefDetail)
def chef_status(chef_id:UUID,payload:ChefStatusUpdate,request:Request,admin:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).update_chef_status(chef_id=chef_id,status=payload.status,reason=payload.reason,admin_id=admin.id,request_id=request.state.request_id)

@router.get("/drivers",response_model=list[AdminDriverListItem])
def drivers(status:str|None=Query(None),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).drivers(status=status,limit=limit,offset=offset)

@router.get("/drivers/{driver_id}",response_model=AdminDriverDetail)
def driver_detail(driver_id:UUID,_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).driver_detail(driver_id)

@router.get("/support/workload-summary",response_model=SupportWorkloadSummary)
def support_summary(_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).support_summary()

@router.get("/finance/summary",response_model=FinanceSummary)
def finance_summary(date_from:date|None=Query(None),date_to:date|None=Query(None),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).finance_summary(date_from,date_to)

@router.get("/audit",response_model=list[AuditItem])
def audit(action:str|None=Query(None),entity_type:str|None=Query(None),actor_user_id:UUID|None=Query(None),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).audit_logs(action=action,entity_type=entity_type,actor_user_id=actor_user_id,limit=limit,offset=offset)

@router.get("/reports/operations",response_model=OperationsReport)
def operations_report(date_from:date|None=Query(None),date_to:date|None=Query(None),_:UserEntity=Depends(admin_user),db:Session=Depends(get_db)): return AdminOperationsService(db).operations_report(date_from,date_to)
