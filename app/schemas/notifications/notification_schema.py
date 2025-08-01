from pydantic import BaseModel
from typing import Optional, List

# Schema para obtener notificaciones
class NotificationData(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    sent_at: str

class GetNotificationsResponse(BaseModel):
    success: bool
    message: str
    data: List[NotificationData]

# Schema para marcar como leída
class MarkAsReadResponse(BaseModel):
    success: bool
    message: str 