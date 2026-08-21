from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.favorites.schemas import (
    FavoriteChefResponse,
    FavoriteDishResponse,
    FavoritesSummaryResponse,
)
from app.modules.favorites.service import FavoriteService

router = APIRouter(prefix="/customer/favorites", tags=["favorites"])


@router.get("/summary", response_model=FavoritesSummaryResponse)
def summary(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> FavoritesSummaryResponse:
    return FavoriteService(db).summary(customer_id=user.id)


@router.get("/chefs", response_model=list[FavoriteChefResponse])
def favorite_chefs(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[FavoriteChefResponse]:
    return FavoriteService(db).list_chefs(customer_id=user.id)


@router.put("/chefs/{chef_id}", response_model=FavoriteChefResponse)
def add_favorite_chef(
    chef_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> FavoriteChefResponse:
    return FavoriteService(db).add_chef(
        customer_id=user.id,
        chef_id=chef_id,
        request_id=request.state.request_id,
    )


@router.delete("/chefs/{chef_id}", status_code=204)
def remove_favorite_chef(
    chef_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    FavoriteService(db).remove_chef(
        customer_id=user.id,
        chef_id=chef_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/dishes", response_model=list[FavoriteDishResponse])
def favorite_dishes(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[FavoriteDishResponse]:
    return FavoriteService(db).list_dishes(customer_id=user.id)


@router.put("/dishes/{dish_id}", response_model=FavoriteDishResponse)
def add_favorite_dish(
    dish_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> FavoriteDishResponse:
    return FavoriteService(db).add_dish(
        customer_id=user.id,
        dish_id=dish_id,
        request_id=request.state.request_id,
    )


@router.delete("/dishes/{dish_id}", status_code=204)
def remove_favorite_dish(
    dish_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    FavoriteService(db).remove_dish(
        customer_id=user.id,
        dish_id=dish_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
