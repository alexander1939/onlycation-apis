from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


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


class MessageResponse(BaseModel):
    """Esquema de respuesta para mensajes"""
    id: int
    chat_id: int
    sender_id: int
    content: str = Field(..., description="Contenido del mensaje (desencriptado)")
    is_read: bool
    is_deleted: bool
    is_encrypted: Optional[bool] = Field(None, description="Indica si el mensaje está encriptado")
    encryption_version: Optional[str] = Field(None, description="Versión de encriptación")
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


class ParticipantResponse(BaseModel):
    """Esquema para información del participante en un chat"""
    id: int
    full_name: str
    model_config = ConfigDict(from_attributes=True)


class ChatSummaryResponse(BaseModel):
    """Esquema para resumen de chat (último mensaje, contador no leídos)"""
    chat_id: int
    student_id: int
    teacher_id: int
    participant: ParticipantResponse
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatSummaryListResponse(BaseModel):
    """Esquema para listar resúmenes de chats"""
    success: bool
    message: str
    data: List[ChatSummaryResponse]
    total: int


# ============================================================================
# ESQUEMA LIGERO PARA LISTA DE CHATS (Preview estilo WhatsApp)
# ============================================================================
class ChatPreview(BaseModel):
    """Elemento ligero para mostrar lista de chats sin mensajes completos."""
    chat_id: int
    participant: ParticipantResponse  # nombre de la otra persona
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class ChatPreviewListResponse(BaseModel):
    success: bool
    message: str
    data: List[ChatPreview]
    total: int


# ============================================================================
# CANDIDATOS DE CHAT (Personas con las que puedes chatear por tener reserva activa)
# ============================================================================
class ChatCandidate(BaseModel):
    participant: ParticipantResponse  # persona con la que puedes chatear (el otro)
    next_booking_start: datetime
    existing_chat_id: Optional[int] = None  # si ya hay chat activo, su ID


class ChatCandidateListResponse(BaseModel):
    success: bool
    message: str
    data: List[ChatCandidate]
    total: int


class ChatEnsureRequest(BaseModel):
    """Solicitud para asegurar/crear un chat con otro usuario (participant)."""
    other_user_id: int
