from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PersonInfo(BaseModel):
    id: int
    first_name: str
    last_name: str


class BookingDetailData(BaseModel):
    booking_id: int
    created_at: datetime
    start_time: datetime
    end_time: datetime
    modality: Optional[str]
    class_link: Optional[str]
    materia: Optional[str]
    status: Optional[str]
    teacher: PersonInfo
    student: PersonInfo
    confirmation_teacher: Optional[bool] = None
    confirmation_student: Optional[bool] = None
    total_paid: Optional[float] = None  # importe total pagado (MXN)


class BookingDetailResponse(BaseModel):
    success: bool
    message: str
    data: BookingDetailData
