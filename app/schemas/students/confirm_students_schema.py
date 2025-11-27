from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class StudentConfirmationCreateRequest(BaseModel):
    
    #payment_booking_id: int 
    confirmation: bool  # True o False
    description_student: str  # Texto obligatorio

    model_config = ConfigDict(from_attributes=True)

class StudentConfirmationData(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    confirmation_date_student: Optional[bool] = None
    description_student: Optional[str] = None   # Lo incluimos en la respuesta

    model_config = ConfigDict(from_attributes=True)

class StudentConfirmationCreateResponse(BaseModel):
    success: bool
    message: str
    data: StudentConfirmationData

# ===== Historial de confirmaciones (Alumno) =====
class StudentConfirmationHistoryItem(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    payment_created_at: Optional[datetime] = None
    booking_start: Optional[datetime] = None
    booking_end: Optional[datetime] = None
    confirmed_by_student: Optional[bool] = None
    confirmed_by_teacher: Optional[bool] = None
    has_assessment_by_student: Optional[bool] = None
    window_status: Optional[str] = None  # open | expired
    confirmable_now: Optional[bool] = None
    seconds_left: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class StudentConfirmationHistoryResponse(BaseModel):
    success: bool
    page: int
    page_size: int
    total: int
    items: list[StudentConfirmationHistoryItem]

class StudentConfirmationHistoryAllResponse(BaseModel):
    success: bool
    offset: int
    limit: int
    total: int
    has_more: bool
    items: list[StudentConfirmationHistoryItem]

class StudentConfirmationRecentHistoryResponse(BaseModel):
    success: bool
    items: list[StudentConfirmationHistoryItem]

class StudentConfirmationAllHistoryResponse(BaseModel):
    success: bool
    offset: int
    limit: int
    total: int
    has_more: bool
    items: list[StudentConfirmationHistoryItem]
