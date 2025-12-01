from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class AssessmentCreate(BaseModel):
    #payment_booking_id: int
    qualification: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=255)

class AssessmentResponse(BaseModel):
    id: int
    user_id: int
    payment_booking_id: int
    qualification: Optional[int]
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AssessmentListResponse(BaseModel):
    success: bool
    message: str
    data: List[AssessmentResponse]

class TeacherCommentResponse(BaseModel):
    id: int
    comment: Optional[str]
    qualification: Optional[int]
    student_id: int
    student_name: str
    created_at: datetime  # 

    class Config:
        orm_mode = True

class TeacherCommentsListResponse(BaseModel):
    success: bool
    message: str
    data: List[TeacherCommentResponse]
