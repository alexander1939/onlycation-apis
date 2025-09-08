from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from typing import List

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
# Get
# -----------------------------
class ForoData(ForoBaseData):
    created_at: datetime
    updated_at: datetime

class ForoResponse(ForoBaseResponse):
    data: Optional[ForoData] = None

# -----------------------------
# UpdateMe (user-specific)
# -----------------------------
class ForoUpdateMeRequest(BaseModel):
    foro_id: int  # ← REQUERIDO: ID del foro a actualizar
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


# # -----------------------------
# # Get All Foros (con paginación)
# # -----------------------------

# class ForoListData(ForoBaseData):
#     created_at: datetime
#     updated_at: datetime

# class ForoListResponse(ForoBaseResponse):
#     total: int
#     offset: int
#     limit: int
#     has_more: bool
#     data: List[ForoListData]



# Foro - List paginated
class ForoListData(BaseModel):
    id: int
    user_id: int
    category_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoListResponse(BaseModel):
    success: bool
    message: str
    data: List[ForoListData]
    total: int
    offset: int
    limit: int
    has_more: bool  