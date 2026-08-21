from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FavoriteChefResponse(BaseModel):
    favorite_id: UUID
    chef_id: UUID
    display_name: str
    specialty: str
    area: str
    rating: float
    is_verified: bool
    is_open_today: bool
    created_at: datetime


class FavoriteDishResponse(BaseModel):
    favorite_id: UUID
    dish_id: UUID
    chef_id: UUID
    name: str
    category: str
    base_price_minor: int
    image_url: str | None
    is_active: bool
    created_at: datetime


class FavoritesSummaryResponse(BaseModel):
    chefs_count: int
    dishes_count: int
