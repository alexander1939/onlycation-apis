from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from typing import List


# ForoReplyComment - Create
class ForoReplyCommentCreateRequest(BaseModel):
    foro_comment_id: int
    comment: str
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentCreateData(BaseModel):
    id: int
    user_id: int
    foro_comment_id: int
    comment: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentCreateResponse(BaseModel):
    success: bool
    message: str
    data: ForoReplyCommentCreateData

# ForoReplyComment - Update
class ForoReplyCommentUpdateRequest(BaseModel):
    comment: str
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentUpdateData(BaseModel):
    id: int
    user_id: int
    foro_comment_id: int
    comment: str
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentUpdateResponse(BaseModel):
    success: bool
    message: str
    data: ForoReplyCommentUpdateData

# ForoReplyComment - Delete
class ForoReplyCommentDeleteResponse(BaseModel):
    success: bool
    message: str

# ForoReplyComment - Get
class ForoReplyCommentData(BaseModel):
    id: int
    user_id: int
    foro_comment_id: int
    comment: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ForoReplyCommentData] = None


class ForoReplyCommentUpdateMeRequest(BaseModel):
    comment: str
    foro_reply_comment_id: Optional[int] = None  # ← CORRECTO: ID de la respuesta
    foro_comment_id: Optional[int] = None        # ← Opcional para búsqueda alternativa
    
    model_config = ConfigDict(from_attributes=True)


class ForoReplyCommentDeleteMeRequest(BaseModel):
    foro_reply_comment_id: Optional[int] = None  # ← CORRECTO: ID de la respuesta
    foro_comment_id: Optional[int] = None       # ← Opcional para búsqueda alternativa
    
    model_config = ConfigDict(from_attributes=True)



# ForoReplyComment - List paginated
class ForoReplyCommentListData(BaseModel):
    id: int
    user_id: int
    foro_comment_id: int
    comment: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForoReplyCommentListResponse(BaseModel):
    success: bool
    message: str
    data: List[ForoReplyCommentListData]
    total: int
    offset: int
    limit: int
    has_more: bool