from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AddressCreateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    area: str = Field(min_length=2, max_length=120)
    street: str | None = Field(default=None, max_length=200)
    building: str | None = Field(default=None, max_length=80)
    floor: str | None = Field(default=None, max_length=40)
    apartment: str | None = Field(default=None, max_length=40)
    latitude: str | None = Field(default=None, max_length=32)
    longitude: str | None = Field(default=None, max_length=32)
    is_default: bool = False


class AddressResponse(BaseModel):
    id: UUID
    label: str | None
    area: str
    street: str | None
    building: str | None
    floor: str | None
    apartment: str | None
    latitude: str | None
    longitude: str | None
    is_default: bool

    model_config = {"from_attributes": True}


class SetOrderDeliveryAddressRequest(BaseModel):
    address_id: UUID



class AddressUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    area: str = Field(min_length=2, max_length=120)
    street: str | None = Field(default=None, max_length=200)
    building: str | None = Field(default=None, max_length=80)
    floor: str | None = Field(default=None, max_length=40)
    apartment: str | None = Field(default=None, max_length=40)
    latitude: str | None = Field(default=None, max_length=32)
    longitude: str | None = Field(default=None, max_length=32)
    is_default: bool = False
