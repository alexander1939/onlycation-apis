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


# Moficar perfil
class ProfileUpdateData(BaseModel):
    credential: Optional[str] = None
    gender: Optional[str] = None
    sex: Optional[str] = None
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
class ProfileUpdateResponse(BaseModel):
    success: bool
    message: str
    data: ProfileUpdateData


# Obtener perfil
class ProfileData(BaseModel):
    credential: Optional[str] = None
    gender: Optional[str] = None
    sex: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ProfileData] = None


# Crear perfil
class ProfileCreateData(BaseModel):
    credential: Optional[str] = None
    gender: Optional[str] = None
    sex: Optional[str] = None
    created_at: datetime  # Solo incluye created_at
    
    model_config = ConfigDict(from_attributes=True)
class ProfileCreateResponse(BaseModel):
    success: bool
    message: str
    data: ProfileCreateData