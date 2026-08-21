from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.addresses.schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
    SetOrderDeliveryAddressRequest,
)
from app.modules.addresses.service import AddressService

router = APIRouter(prefix="/customer", tags=["addresses"])


@router.get("/addresses", response_model=list[AddressResponse])
def list_addresses(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[AddressResponse]:
    return AddressService(db).list_addresses(customer_id=user.id)


@router.post("/addresses", response_model=AddressResponse, status_code=201)
def create_address(
    payload: AddressCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> AddressResponse:
    return AddressService(db).create_address(
        customer_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )




@router.patch("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: UUID,
    payload: AddressUpdateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> AddressResponse:
    return AddressService(db).update_address(
        customer_id=user.id,
        address_id=address_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post("/addresses/{address_id}/default", response_model=AddressResponse)
def set_default_address(
    address_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> AddressResponse:
    return AddressService(db).set_default(
        customer_id=user.id,
        address_id=address_id,
        request_id=request.state.request_id,
    )


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    AddressService(db).delete_address(
        customer_id=user.id,
        address_id=address_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/orders/{order_id}/delivery-address")
def set_order_delivery_address(
    order_id: UUID,
    payload: SetOrderDeliveryAddressRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = AddressService(db).snapshot_for_order(
        customer_id=user.id,
        order_id=order_id,
        address_id=payload.address_id,
        request_id=request.state.request_id,
    )
    return {
        "order_id": str(row.order_id),
        "address_id": str(row.source_address_id) if row.source_address_id else None,
        "area": row.area,
        "street": row.street,
        "building": row.building,
        "floor": row.floor,
        "apartment": row.apartment,
    }
