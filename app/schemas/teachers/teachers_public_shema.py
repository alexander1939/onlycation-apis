from pydantic import BaseModel
from typing import Optional

class PublicTeacherProfile(BaseModel):
    teacher_id: int
    first_name: str
    last_name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    price_per_class: Optional[float] = None   # ✅ ahora opcional
    educational_level: Optional[str] = None   # ✅ ahora opcional
    total_bookings: int
    
    class Config:
        from_attributes = True
