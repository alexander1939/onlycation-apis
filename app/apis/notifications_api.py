from fastapi import APIRouter, Depends, Query, HTTPException
from app.schemas.notifications.notification_schema import (
    GetNotificationsResponse, MarkAsReadResponse
)
from app.services.notifications import (
    get_user_notifications, 
    mark_notification_as_read
)
from app.apis.deps import auth_required, get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/mis-notificaciones", response_model=GetNotificationsResponse)
async def obtener_notificaciones(
    limit: int = Query(10, ge=1, le=50, description="Número máximo de notificaciones"),
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtiene las notificaciones del usuario autenticado
    """
    result = await get_user_notifications(db, user_data.get("user_id"), limit)
    
    return {
        "success": result["success"],
        "message": result["message"],
        "data": result["data"]
    }

@router.put("/marcar-leida/{notification_id}", response_model=MarkAsReadResponse)
async def marcar_como_leida(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Marca una notificación como leída
    """
    result = await mark_notification_as_read(db, user_data.get("user_id"), notification_id)
    
    return {
        "success": result["success"],
        "message": result["message"]
    } 