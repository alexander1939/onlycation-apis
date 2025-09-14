from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

# -----------------------------
# Base Models
# -----------------------------
class ForoReplyCommentBaseData(BaseModel):
    id: int
    user_id: int
    foro_comment_id: int
    comment: str

    model_config = ConfigDict(from_attributes=True)


class ForoReplyCommentBaseResponse(BaseModel):
    success: bool
    message: str


# -----------------------------
# Create
# -----------------------------
class ForoReplyCommentCreateRequest(BaseModel):
    foro_comment_id: int
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class ForoReplyCommentCreateData(ForoReplyCommentBaseData):
    created_at: datetime


class ForoReplyCommentCreateResponse(ForoReplyCommentBaseResponse):
    data: ForoReplyCommentCreateData


# -----------------------------
# Update
# -----------------------------
class ForoReplyCommentUpdateRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class ForoReplyCommentUpdateData(ForoReplyCommentBaseData):
    updated_at: datetime


class ForoReplyCommentUpdateResponse(ForoReplyCommentBaseResponse):
    data: ForoReplyCommentUpdateData


# -----------------------------
# Delete
# -----------------------------
class ForoReplyCommentDeleteResponse(ForoReplyCommentBaseResponse):
    pass


# -----------------------------
# Get (single)
# -----------------------------
class ForoReplyCommentData(ForoReplyCommentBaseData):
    created_at: datetime
    updated_at: datetime


class ForoReplyCommentResponse(ForoReplyCommentBaseResponse):
    data: Optional[ForoReplyCommentData] = None


# -----------------------------
# List (multiple / paginated)
# -----------------------------
class ForoReplyCommentListData(ForoReplyCommentData):
    pass  # Reutiliza ForoReplyCommentData


class ForoReplyCommentListResponse(ForoReplyCommentBaseResponse):
    data: List[ForoReplyCommentListData]
    total: int
    offset: int
    limit: int
    has_more: bool


# -----------------------------
# User-specific
# -----------------------------
class ForoReplyCommentUpdateMeRequest(BaseModel):
    foro_reply_comment_id: Optional[int] = None  # ← ID de la respuesta
    foro_comment_id: Optional[int] = None        # ← Alternativa de búsqueda
    comment: str = Field(..., min_length=1, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)


class ForoReplyCommentDeleteMeRequest(BaseModel):
    foro_reply_comment_id: Optional[int] = None  # ← ID de la respuesta
    foro_comment_id: Optional[int] = None        # ← Alternativa de búsqueda
    
    model_config = ConfigDict(from_attributes=True)
