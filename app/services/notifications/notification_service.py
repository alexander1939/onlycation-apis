from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.notifications.notifications import Notification
from app.models.notifications.user_notifications import User_notification
from app.models.users import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validation.exception import unexpected_exception
from datetime import datetime

async def create_welcome_notification(db: AsyncSession, user: User):
    """
    Crea una notificación de bienvenida para un usuario que se acaba de suscribir
    """
    try:
        # Buscar si ya existe una notificación de bienvenida
        existing_notification = await db.execute(
            select(Notification).where(
                Notification.title == "¡Bienvenido a OnlyCation!",
                Notification.type == "welcome"
            )
        )
        notification = existing_notification.scalar_one_or_none()
        
        # Si no existe, crear la notificación
        if not notification:
            notification = Notification(
                title="¡Bienvenido a OnlyCation!",
                message="¡Gracias por suscribirte! Ahora tienes acceso a todos nuestros servicios premium. Disfruta de tu experiencia de aprendizaje.",
                type="welcome"
            )
            db.add(notification)
            await db.commit()
            await db.refresh(notification)
        
        # Crear la notificación para el usuario específico
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=user.id,
            is_read=False
        )
        
        db.add(user_notification)
        await db.commit()
        await db.refresh(user_notification)
        
        return {
            "success": True,
            "message": "Notificación de bienvenida creada exitosamente",
            "data": {
                "notification_id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "user_notification_id": user_notification.id
            }
        }
        
    except Exception as e:
        await db.rollback()
        await unexpected_exception()

async def create_subscription_notification(db: AsyncSession, user: User, plan_name: str):
    """
    Crea una notificación específica de suscripción
    """
    try:
        # Crear notificación de suscripción
        notification = Notification(
            title=f"Suscripción activada - {plan_name}",
            message=f"Tu suscripción al plan {plan_name} ha sido activada exitosamente. ¡Disfruta de todos los beneficios!",
            type="subscription"
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        # Asignar al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=user.id,
            is_read=False
        )
        
        db.add(user_notification)
        await db.commit()
        await db.refresh(user_notification)
        
        return {
            "success": True,
            "message": "Notificación de suscripción creada exitosamente",
            "data": {
                "notification_id": notification.id,
                "title": notification.title,
                "message": notification.message
            }
        }
        
    except Exception as e:
        await db.rollback()
        await unexpected_exception()

async def get_user_notifications(db: AsyncSession, user_id: int, limit: int = 10):
    """
    Obtiene las notificaciones de un usuario
    """
    try:
        notifications_result = await db.execute(
            select(User_notification)
            .options(joinedload(User_notification.notification))
            .where(User_notification.user_id == user_id)
            .order_by(User_notification.sent_at.desc())
            .limit(limit)
        )
        
        notifications = notifications_result.scalars().all()
        
        return {
            "success": True,
            "message": "Notificaciones obtenidas exitosamente",
            "data": [
                {
                    "id": un.id,
                    "title": un.notification.title,
                    "message": un.notification.message,
                    "type": un.notification.type,
                    "is_read": un.is_read,
                    "sent_at": un.sent_at.isoformat()
                } for un in notifications
            ]
        }
        
    except Exception as e:
        await unexpected_exception()

async def mark_notification_as_read(db: AsyncSession, user_id: int, notification_id: int):
    """
    Marca una notificación como leída
    """
    try:
        notification_result = await db.execute(
            select(User_notification).where(
                User_notification.id == notification_id,
                User_notification.user_id == user_id
            )
        )
        
        notification = notification_result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        
        return {
            "success": True,
            "message": "Notificación marcada como leída"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        await unexpected_exception() 