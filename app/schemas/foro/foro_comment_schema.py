from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

# -----------------------------
# Base Models
# -----------------------------
class ForoCommentBaseData(BaseModel):
    id: int
    user_id: int
    foro_id: int
    comment: str

    model_config = ConfigDict(from_attributes=True)

class ForoCommentBaseResponse(BaseModel):
    success: bool
    message: str

# -----------------------------
# Create
# -----------------------------
class ForoCommentCreateRequest(BaseModel):
    foro_id: int
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoCommentCreateData(ForoCommentBaseData):
    created_at: datetime

class ForoCommentCreateResponse(ForoCommentBaseResponse):
    data: ForoCommentCreateData

# -----------------------------
# Update
# -----------------------------
class ForoCommentUpdateRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class ForoCommentUpdateData(ForoCommentBaseData):
    updated_at: datetime

class ForoCommentUpdateResponse(ForoCommentBaseResponse):
    data: ForoCommentUpdateData

# -----------------------------
# Delete
# -----------------------------
class ForoCommentDeleteResponse(ForoCommentBaseResponse):
    pass


# -----------------------------
# Get (single)
# -----------------------------
class ForoCommentData(ForoCommentBaseData):
    created_at: datetime
    updated_at: datetime

class ForoCommentResponse(ForoCommentBaseResponse):
    data: Optional[ForoCommentData] = None


# -----------------------------
# List (multiple / paginated)
# -----------------------------
class ForoCommentListData(ForoCommentData):
    pass  # Reutiliza ForoCommentData


class ForoCommentListResponse(ForoCommentBaseResponse):
    data: List[ForoCommentListData]
    total: int
    offset: int
    limit: int
    has_more: bool

# -----------------------------
# User-specific
# -----------------------------
class ForoCommentUpdateMeRequest(BaseModel):
    foro_comment_id: Optional[int] = None  # ← ID del comentario
    foro_id: Optional[int] = None          # ← Alternativa de búsqueda
    comment: str = Field(..., min_length=1, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)


class ForoCommentDeleteMeRequest(BaseModel):
    foro_comment_id: Optional[int] = None  # ← ID del comentario
    foro_id: Optional[int] = None          # ← Alternativa de búsqueda
    
    model_config = ConfigDict(from_attributes=True)
