from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PublicTeacherProfile(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    educational_level: Optional[str] = None
    expertise_area: Optional[str] = None
    price_per_hour: Optional[float] = None
    average_rating: Optional[float] = None
    video_embed_url: Optional[str] = None
    video_thumbnail_url: Optional[str] = None
    total_bookings: int
    
    class Config:
        from_attributes = True

class PublicTeacherProfile2(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    availability_count: int
    booking_count: int
    profile_complete: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas para búsqueda de catálogo de docentes
class TeacherSearchResult(BaseModel):
    """Resultado de búsqueda de un docente"""
    user_id: int
    first_name: str
    last_name: str
    educational_level: Optional[str] = None
    expertise_area: Optional[str] = None
    price_per_hour: Optional[float] = None
    average_rating: Optional[float] = None
    video_embed_url: Optional[str] = None
    video_thumbnail_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class TeacherSearchResponse(BaseModel):
    """Respuesta de búsqueda de docentes"""
    success: bool
    message: str
    data: list[TeacherSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int
