from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

# -----------------------------
# Base Models
# -----------------------------
class ForoBaseData(BaseModel):
    id: int
    user_id: int
    category_id: int
    title: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ForoBaseResponse(BaseModel):
    success: bool
    message: str

# -----------------------------
# Create
# -----------------------------
class ForoCreateRequest(BaseModel):
    category_id: int
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoCreateData(ForoBaseData):
    created_at: datetime

class ForoCreateResponse(ForoBaseResponse):
    data: ForoCreateData

# -----------------------------
# Update
# -----------------------------
class ForoUpdateRequest(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoUpdateData(ForoBaseData):
    updated_at: datetime

class ForoUpdateResponse(ForoBaseResponse):
    data: ForoUpdateData

# -----------------------------
# Get (single)
# -----------------------------
class ForoData(ForoBaseData):
    created_at: datetime
    updated_at: datetime

class ForoResponse(ForoBaseResponse):
    data: Optional[ForoData] = None


# -----------------------------
# List (multiple)
# -----------------------------
class ForoListData(ForoData):
    pass  # reutiliza ForoData (puedes extender si necesitas algo distinto)

class ForoListResponse(ForoBaseResponse):
    data: List[ForoListData]
    total: int
    offset: int
    limit: int
    has_more: bool

# -----------------------------
# UpdateMe (user-specific)
# -----------------------------
class ForoUpdateMeRequest(BaseModel):
    foro_id: int  # ← REQUERIDO: ID del foro a actualizar
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
