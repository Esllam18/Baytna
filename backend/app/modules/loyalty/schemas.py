from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LoyaltyTransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    points: int
    source_order_id: UUID | None
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoyaltyAccountResponse(BaseModel):
    customer_id: UUID
    balance_points: int
    lifetime_earned_points: int
    lifetime_redeemed_points: int
    transactions: list[LoyaltyTransactionResponse]
