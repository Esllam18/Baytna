from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.pricing.schemas import PricingQuoteRequest, PricingQuoteResponse
from app.modules.pricing.service import PricingService

router = APIRouter(prefix="/customer/pricing", tags=["pricing"])

@router.post("/quote", response_model=PricingQuoteResponse)
def quote(payload: PricingQuoteRequest, user: UserEntity = Depends(current_user), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> PricingQuoteResponse:
    service = PricingService(db, settings)
    data = service.quote_cart(customer_id=user.id, cart_id=payload.cart_id, coupon_code=payload.coupon_code, loyalty_points_to_redeem=payload.loyalty_points_to_redeem)
    return service.quote_response(data)
