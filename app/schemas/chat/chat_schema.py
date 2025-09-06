from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# ESQUEMAS PARA CHATS
# ============================================================================

class ChatBase(BaseModel):
    """Esquema base para chats"""
    student_id: int = Field(..., description="ID del estudiante")
    teacher_id: int = Field(..., description="ID del profesor")


class ChatCreateRequest(BaseModel):
    """Esquema para crear un nuevo chat"""
    teacher_id: int = Field(..., description="ID del profesor")


class ChatResponse(ChatBase):
    """Esquema de respuesta para chats"""
    id: int
    is_active: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Esquema para listar chats"""
    success: bool
    message: str
    data: List[ChatResponse]
    total: int


# ============================================================================
# ESQUEMAS PARA MENSAJES
# ============================================================================

class MessageBase(BaseModel):
    """Esquema base para mensajes"""
    content: str = Field(..., min_length=1, max_length=1000, description="Contenido del mensaje")


class MessageCreateRequest(MessageBase):
    """Esquema para crear un nuevo mensaje"""
    chat_id: int = Field(..., description="ID del chat")


class MessageResponse(MessageBase):
    """Esquema de respuesta para mensajes"""
    id: int
    chat_id: int
    sender_id: int
    is_read: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Esquema para listar mensajes de un chat"""
    success: bool
    message: str
    data: List[MessageResponse]
    total: int
    chat_id: int


# ============================================================================
# ESQUEMAS PARA OPERACIONES ESPECIALES
# ============================================================================

class MarkAsReadRequest(BaseModel):
    """Esquema para marcar mensajes como leídos"""
    message_ids: List[int] = Field(..., description="IDs de los mensajes a marcar como leídos")


class ChatSummaryResponse(BaseModel):
    """Esquema para resumen de chat (último mensaje, contador no leídos)"""
    chat_id: int
    student_id: int
    teacher_id: int
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatSummaryListResponse(BaseModel):
    """Esquema para listar resúmenes de chats"""
    success: bool
    message: str
    data: List[ChatSummaryResponse]
    total: int
