from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PriceCreateRequest(BaseModel):
    preference_id: int
    price_range_id: int
    selected_prices: float
    extra_hour_price: float

class PriceCreateData(BaseModel):
    id: int
    preference_id: int
    price_range_id: int
    selected_prices: float
    extra_hour_price: float
    created_at: datetime

class PriceCreateResponse(BaseModel):
    success: bool
    message: str
    data: PriceCreateData

class PriceReadResponse(BaseModel):
    success: bool
    message: str
    data: Optional[list[PriceCreateData]]
