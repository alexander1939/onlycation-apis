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


async def create_booking_payment_notification(db: AsyncSession, user_id: int, payment_booking_id: int):
    """
    Crea una notificación de confirmación de pago de reserva
    solo si no existe previamente.
    """
    try:
        # Verificar si ya existe una notificación para este pago
        existing = await db.execute(
            select(User_notification)
            .join(Notification)
            .where(
                User_notification.user_id == user_id,
                Notification.type == "booking_payment",
            )
        )
        if existing.scalar_one_or_none():
            return  # Ya existe, no creamos otra

        # Crear la notificación base (solo una vez para este tipo+referencia)
        notification = Notification(
            title="Pago de reserva confirmado",
            message="Tu pago para la reserva ha sido confirmado con éxito.",
            type="booking_payment",
        )
        db.add(notification)
        await db.flush()

        # Asociar la notificación al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=user_id,
            is_read=False
        )
        db.add(user_notification)

        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def create_teacher_booking_notification(
    db: AsyncSession, teacher_id: int, booking_id: int, start_time: datetime, end_time: datetime
):
    """
    Crea una notificación para el profesor sobre una nueva reserva.
    """
    try:
        # Verificar si ya existe una notificación para esta reserva
        existing = await db.execute(
            select(User_notification)
            .join(Notification)
            .where(
                User_notification.user_id == teacher_id,
                Notification.type == "new_booking",
            )
        )
        if existing.scalar_one_or_none():
            return  # Ya existe, no duplicar

        # Crear la notificación base
        notification = Notification(
            title="Nueva reserva recibida",
            message=f"Tienes una nueva reserva programada para el {start_time.strftime('%d/%m/%Y %H:%M')} hasta el {end_time.strftime('%d/%m/%Y %H:%M')}.",
            type="new_booking",
        )
        db.add(notification)
        await db.flush()

        # Asociar la notificación al profesor
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=teacher_id,
            is_read=False
        )
        db.add(user_notification)

        await db.commit()
    except Exception:
        await db.rollback()
        raise

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

async def create_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: str,
    notification_type: str
):
    """
    Crea una notificación genérica para un usuario
    """
    try:
        # Crear la notificación base
        notification = Notification(
            title=title,
            message=message,
            type=notification_type
        )
        db.add(notification)
        await db.flush()

        # Asociar la notificación al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=user_id,
            is_read=False
        )
        db.add(user_notification)

        await db.commit()
        
        return {
            "success": True,
            "notification_id": notification.id,
            "user_notification_id": user_notification.id
        }
        
    except Exception as e:
        await db.rollback()
        raise e 