from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TeacherRescheduleRequestCreate(BaseModel):
    booking_id: int
    new_availability_id: int
    new_start_time: datetime
    new_end_time: datetime
    reason: Optional[str] = None

class StudentRescheduleResponse(BaseModel):
    request_id: int
    approved: bool
    response_message: Optional[str] = None

class RescheduleRequestResponse(BaseModel):
    id: int
    booking_id: int
    teacher_id: int
    student_id: int
    current_start_time: datetime
    current_end_time: datetime
    new_start_time: datetime
    new_end_time: datetime
    reason: Optional[str]
    status: str
    student_response: Optional[str]
    created_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime]

class RescheduleRequestList(BaseModel):
    requests: list[RescheduleRequestResponse]
    total: int
