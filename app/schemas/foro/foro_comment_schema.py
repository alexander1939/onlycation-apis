from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from typing import List


# Base Models
class ForoCommentBaseData(BaseModel):
    id: int
    user_id: int
    foro_id: int
    comment: str

    model_config = ConfigDict(from_attributes=True)

class ForoCommentBaseResponse(BaseModel):
    success: bool
    message: str

# Create
class ForoCommentCreateRequest(BaseModel):
    foro_id: int
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoCommentCreateData(ForoCommentBaseData):
    created_at: datetime

class ForoCommentCreateResponse(ForoCommentBaseResponse):
    data: ForoCommentCreateData

# Update
class ForoCommentUpdateRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoCommentUpdateData(ForoCommentBaseData):
    updated_at: datetime

class ForoCommentUpdateResponse(ForoCommentBaseResponse):
    data: ForoCommentUpdateData

# Delete
class ForoCommentDeleteResponse(ForoCommentBaseResponse):
    pass

# Get
class ForoCommentData(ForoCommentBaseData):
    created_at: datetime
    updated_at: datetime

class ForoCommentResponse(ForoCommentBaseResponse):
    data: Optional[ForoCommentData] = None

# User-specific
class ForoCommentUpdateMeRequest(BaseModel):
    comment: str
    foro_comment_id: Optional[int] = None  # ← CORRECTO: ID del comentario
    foro_id: Optional[int] = None          # ← Opcional para búsqueda alternativa
    
    model_config = ConfigDict(from_attributes=True)

class ForoCommentDeleteMeRequest(BaseModel):
    foro_comment_id: Optional[int] = None  # ← CORRECTO: ID del comentario
    foro_id: Optional[int] = None          # ← Opcional para búsqueda alternativa
    
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Get All ForoComments (con paginación)
# -----------------------------
# ForoComment - List paginated
class ForoCommentListData(BaseModel):
    id: int
    user_id: int
    foro_id: int
    comment: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoCommentListResponse(BaseModel):
    success: bool
    message: str
    data: List[ForoCommentListData]
    total: int
    offset: int
    limit: int
    has_more: bool