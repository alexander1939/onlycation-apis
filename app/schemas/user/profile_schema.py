from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

"""
Modelo que representa la estructura de datos recibida y enviada en las APIs de Profile
"""

class ProfileCreateRequest(BaseModel):
    user_id: int
    credential: Optional[str] = None
    gender: Optional[str] = None
    sex: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProfileUpdateRequest(BaseModel):
    credential: Optional[str] = None
    gender: Optional[str] = None
    sex: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProfileData(BaseModel):
    id: int
    user_id: int
    credential: Optional[str]
    gender: Optional[str]
    sex: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ProfileData] = None

class ProfileListResponse(BaseModel):
    success: bool
    message: str
    data: Optional[list[ProfileData]] = None