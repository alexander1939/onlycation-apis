from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UpcomingBookingItem(BaseModel):
    booking_id: int
    availability_id: int
    start_time: datetime
    end_time: datetime
    materia: str | None
    modality: str | None
    participant_role: str  # "teacher" o "student" respecto al usuario autenticado
    status: Optional[str] = None


class UpcomingBookingsResponse(BaseModel):
    success: bool
    message: str
    data: List[UpcomingBookingItem]
    total: int
    offset: int
    limit: int
    has_more: bool
