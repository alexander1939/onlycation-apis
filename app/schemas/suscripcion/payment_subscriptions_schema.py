from pydantic import BaseModel
from typing import Optional, List

# Schemas para crear suscripción
class SubscribeRequest(BaseModel):
    plan_id: int

class SubscribeResponse(BaseModel):
    success: bool
    message: str
    data: dict

# Schemas para verificar pago
class VerifyPaymentRequest(BaseModel):
    session_id: str

class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    payment_status: Optional[str] = None
    data: Optional[dict] = None

# Schemas para webhook
class WebhookResponse(BaseModel):
    success: bool
    message: str

# Schema para obtener suscripción del usuario
class UserSubscriptionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Schema para cancelar suscripción
class CancelSubscriptionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
