from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime
from typing import Optional
import logging

from app.models.notifications.notifications import Notification
from app.models.notifications.user_notifications import User_notification
from app.models.users.user import User

logger = logging.getLogger(__name__)


async def send_booking_confirmation_to_student(
    db: AsyncSession, 
    student_id: int, 
    booking_details: dict
) -> bool:
    """
    Enviar notificación de confirmación de reserva al estudiante
    """
    try:
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == "booking_confirmed_student").limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title="¡Reserva confirmada!",
                message="Tu reserva ha sido confirmada exitosamente.",
                type="booking_confirmed_student"
            )
            db.add(notification)
            await db.flush()
        
        # Asociar al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=student_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de confirmación enviada al estudiante {student_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación al estudiante: {str(e)}")
        return False

async def send_booking_notification_to_teacher(
    db: AsyncSession, 
    teacher_id: int, 
    booking_details: dict
) -> bool:
    """
    Enviar notificación de nueva reserva al docente
    """
    try:
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == "booking_confirmed_teacher").limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title="Nueva reserva recibida",
                message="Tienes una nueva reserva. Revisa los detalles en tu panel.",
                type="booking_confirmed_teacher"
            )
            db.add(notification)
            await db.flush()
        
        # Asociar al docente
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=teacher_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de nueva reserva enviada al docente {teacher_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación al docente: {str(e)}")
        return False

async def send_payment_confirmation_notification(
    db: AsyncSession, 
    student_id: int, 
    payment_details: dict
) -> bool:
    """
    Enviar notificación de confirmación de pago
    """
    try:
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == "booking_payment_confirmed").limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title="Pago confirmado",
                message="Tu pago ha sido procesado correctamente.",
                type="booking_payment_confirmed"
            )
            db.add(notification)
            await db.flush()
        
        # Asociar al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=student_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de pago enviada al estudiante {student_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación de pago: {str(e)}")
        return False

async def send_reschedule_request_notification(
    db: AsyncSession, 
    student_id: int, 
    reschedule_details: dict
) -> bool:
    """
    Enviar notificación al estudiante sobre solicitud de reagendado del docente
    """
    try:
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == "reschedule_request_received").limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title="Solicitud de reagendado",
                message="Has recibido una solicitud para reagendar una clase. Revisa los detalles y responde.",
                type="reschedule_request_received"
            )
            db.add(notification)
            await db.flush()
        
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=student_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de solicitud de reagendado enviada al estudiante {student_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación de reagendado: {str(e)}")
        return False

async def send_reschedule_response_notification(
    db: AsyncSession, 
    teacher_id: int, 
    response_details: dict
) -> bool:
    """
    Enviar notificación al docente sobre la respuesta del estudiante al reagendado
    """
    try:
        notification_type = "reschedule_approved" if response_details.get('approved') else "reschedule_rejected"
        action = "aprobado" if response_details.get('approved') else "rechazado"
        title = "Reagendado aprobado" if response_details.get('approved') else "Reagendado rechazado"
        
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == notification_type).limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title=title,
                message=f"Tu solicitud de reagendado ha sido {action}.",
                type=notification_type
            )
            db.add(notification)
            await db.flush()
        
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=teacher_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de respuesta de reagendado enviada al docente {teacher_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación de respuesta: {str(e)}")
        return False


async def send_booking_rescheduled_notification(
    db: AsyncSession, 
    user_id: int, 
    notification_details: dict
) -> bool:
    """
    Enviar notificación cuando una reserva ha sido reagendada (para estudiante y docente)
    """
    try:
        # Verificar si ya existe una notificación de este tipo
        existing_notification = await db.execute(
            select(Notification).where(Notification.type == "booking_rescheduled").limit(1)
        )
        notification = existing_notification.scalar_one_or_none()
        
        if not notification:
            # Crear notificación si no existe
            notification = Notification(
                title="Reserva reagendada",
                message="Una de tus reservas ha sido reagendada. Revisa los nuevos detalles en tu panel.",
                type="booking_rescheduled"
            )
            db.add(notification)
            await db.flush()
        
        # Asociar al usuario
        user_notification = User_notification(
            notification_id=notification.id,
            user_id=user_id,
            is_read=False
        )
        db.add(user_notification)
        await db.commit()
        
        logger.info(f"✅ Notificación de reagendado enviada al usuario {user_id}")
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error enviando notificación de reagendado: {str(e)}")
        return False
