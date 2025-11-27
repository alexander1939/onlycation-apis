from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ConfirmationCreateRequest(BaseModel):
    #student_id: int
    #payment_booking_id: int 
    confirmation: bool  # True o False
    description_teacher: str  # Texto obligatorio

    model_config = ConfigDict(from_attributes=True)

class ConfirmationData(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    confirmation_date_teacher: Optional[bool] = None
    evidence_teacher: Optional[str] = None
    description_teacher: Optional[str] = None   # Lo incluimos en la respuesta

    model_config = ConfigDict(from_attributes=True)

class ConfirmationCreateResponse(BaseModel):
    success: bool
    message: str
    data: ConfirmationData

# ===== Historial de confirmaciones (Docente) =====
class TeacherConfirmationHistoryItem(BaseModel):
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

class TeacherConfirmationHistoryResponse(BaseModel):
    success: bool
    page: int
    page_size: int
    total: int
    items: list[TeacherConfirmationHistoryItem]

class TeacherConfirmationHistoryAllResponse(BaseModel):
    success: bool
    offset: int
    limit: int
    total: int
    has_more: bool
    items: list[TeacherConfirmationHistoryItem]

class TeacherConfirmationRecentHistoryResponse(BaseModel):
    success: bool
    items: list[TeacherConfirmationHistoryItem]

class TeacherConfirmationAllHistoryResponse(BaseModel):
    success: bool
    offset: int
    limit: int
    total: int
    has_more: bool
    items: list[TeacherConfirmationHistoryItem]

# ===== Detalle de confirmación (para docente/estudiante) =====
class ConfirmationDetail(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    booking_start: Optional[datetime] = None
    booking_end: Optional[datetime] = None
    confirmed_by_student: Optional[bool] = None
    confirmed_by_teacher: Optional[bool] = None
    evidence_student: Optional[str] = None
    evidence_teacher: Optional[str] = None
    description_student: Optional[str] = None
    description_teacher: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ConfirmationDetailResponse(BaseModel):
    success: bool
    data: ConfirmationDetail
