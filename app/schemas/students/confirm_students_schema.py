from pydantic import BaseModel, ConfigDict
from typing import Optional

class StudentConfirmationCreateRequest(BaseModel):
    
    #payment_booking_id: int 
    confirmation: bool  # True o False
    description_student: str  # 🔹 Texto obligatorio

    model_config = ConfigDict(from_attributes=True)

class StudentConfirmationData(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    payment_booking_id: int
    confirmation_date_student: Optional[bool] = None
    description_student: Optional[str] = None   # 🔹 Lo incluimos en la respuesta

    model_config = ConfigDict(from_attributes=True)

class StudentConfirmationCreateResponse(BaseModel):
    success: bool
    message: str
    data: StudentConfirmationData
