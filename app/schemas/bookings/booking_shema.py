from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class BookingSegment(BaseModel):
    availability_id: int
    start_time: datetime
    end_time: datetime

class BookingRequest(BaseModel):
    availability_id: int
    price_id: int
    start_time: datetime
    end_time: datetime
    total_hours: int  
    # Campos opcionales para compras multi-tramos en una sola sesión
    availability_ids: Optional[List[int]] = None
    items: Optional[List[BookingSegment]] = None

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

class RescheduleBookingRequest(BaseModel):
    booking_id: int
    new_availability_id: int
    new_start_time: datetime
    new_end_time: datetime

class RescheduleBookingResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None