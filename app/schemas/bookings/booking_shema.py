from pydantic import BaseModel
from typing import Optional, Dict

class BookingRequest(BaseModel):
    availability_id: int
    price_id: int
    start_time: str
    end_time: str
    total_hours: int  # <--- Nuevo campo

class BookingPaymentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

class VerifyBookingPaymentRequest(BaseModel):
    session_id: str

class VerifyBookingPaymentResponse(BaseModel):
    success: bool
    message: str
    payment_status: Optional[str] = None
    data: Optional[Dict] = None