from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ConfirmationCreateRequest(BaseModel):
    #student_id: int
    #payment_booking_id: int 
    confirmation: bool  # True o False
    description_teacher: str  # 🔹 Texto obligatorio

    model_config = ConfigDict(from_attributes=True)

class ConfirmationData(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    confirmation_date_teacher: Optional[bool] = None
    evidence_teacher: Optional[str] = None
    description_teacher: Optional[str] = None   # 🔹 Lo incluimos en la respuesta

    model_config = ConfigDict(from_attributes=True)

class ConfirmationCreateResponse(BaseModel):
    success: bool
    message: str
    data: ConfirmationData

