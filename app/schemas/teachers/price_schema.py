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

class PriceRangeItem(BaseModel):
    id: int
    minimum_price: float
    maximum_price: float

class PriceAvailabilityData(BaseModel):
    preference_id: int
    educational_level_id: int
    price_ranges: list[PriceRangeItem]

class PriceAvailabilityResponse(BaseModel):
    success: bool
    message: str
    data: PriceAvailabilityData

# ================= Update Price Schemas =================
class PriceUpdateRequest(BaseModel):
    """Payload para actualizar el precio base del docente.
    - selected_prices: nuevo precio base por hora
    - price_range_id: opcional, si cambia de rango (debe corresponder al mismo nivel educativo de su preferencia)
    """
    selected_prices: float
    price_range_id: Optional[int] = None

class PriceUpdateData(BaseModel):
    id: int
    preference_id: int
    price_range_id: int
    selected_prices: float
    extra_hour_price: float
    created_at: datetime
    updated_at: datetime

class PriceUpdateResponse(BaseModel):
    success: bool
    message: str
    data: PriceUpdateData
