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

class BookingQuoteRequest(BaseModel):
    # Para cotización pública: soporta modo single y multi-segmentos
    items: Optional[List[BookingSegment]] = None
    availability_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BookingQuoteResponse(BaseModel):
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
    # Modo simple (compatibilidad)
    new_availability_id: Optional[int] = None
    new_start_time: Optional[datetime] = None
    new_end_time: Optional[datetime] = None
    # Modo avanzado: lista de tramos por hora (como en BookingRequest.items)
    items: Optional[List[BookingSegment]] = None

class RescheduleBookingResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None