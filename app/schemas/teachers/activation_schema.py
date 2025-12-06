from pydantic import BaseModel
from typing import List, Optional


class ActivationCheckData(BaseModel):
    has_preference: bool
    has_price: bool
    has_wallet: bool
    has_availability: bool
    has_video: bool
    has_documents: bool
    missing: List[str]
    # Opcionales para reflejar estado de Stripe Connect
    stripe_status: Optional[str] = None
    stripe_setup_url: Optional[str] = None


class ActivationCheckResponse(BaseModel):
    success: bool
    message: str
    data: ActivationCheckData


class ActivationPerformResponse(BaseModel):
    success: bool
    message: str
    data: ActivationCheckData
