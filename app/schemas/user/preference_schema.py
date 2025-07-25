from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

"""
Modelo que representa la estructura de datos recibida y enviada en las APIs de Preference
"""

class PreferenceCreateRequest(BaseModel):
    educational_level_id: Optional[int] = None
    modality_id: Optional[int] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class PreferenceUpdateRequest(BaseModel):
    educational_level_id: Optional[int] = None
    modality_id: Optional[int] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Modificar preferencias
class PreferenceUpdateData(BaseModel):
    educational_level_id: Optional[int] = None
    modality_id: Optional[int] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PreferenceUpdateResponse(BaseModel):
    success: bool
    message: str
    data: PreferenceUpdateData

# Obtener preferencias
class PreferenceData(BaseModel):
    educational_level_id: Optional[int] = None
    modality_id: Optional[int] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class PreferenceResponse(BaseModel):
    success: bool
    message: str
    data: Optional[PreferenceData] = None

# Crear preferencias
class PreferenceCreateData(BaseModel):
    educational_level_id: Optional[int] = None
    modality_id: Optional[int] = None
    location: Optional[str] = None
    location_description: Optional[str] = None
    created_at: datetime  # Solo incluye created_at
    
    model_config = ConfigDict(from_attributes=True)

class PreferenceCreateResponse(BaseModel):
    success: bool
    message: str
    data: PreferenceCreateData