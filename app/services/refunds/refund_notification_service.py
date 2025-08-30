from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models.booking.confirmation import Confirmation
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.users.user import User
from app.services.notifications.booking_notification_service import (
    send_refund_processed_notification
)
from app.services.notifications.booking_email_service import (
    send_refund_processed_email
)
from typing import Dict
import logging

logger = logging.getLogger(__name__)

async def send_refund_notifications(
    db: AsyncSession,
    confirmation: Confirmation,
    refund_amount: int,
    refund_reason: str
) -> Dict:
    """
    Envía notificaciones de refund al estudiante y docente
    """
    try:
        # Obtener el payment_booking con todas las relaciones necesarias
        payment_booking_result = await db.execute(
            select(PaymentBooking).options(
                joinedload(PaymentBooking.booking).joinedload(Booking.availability).joinedload(Availability.user)
            ).where(PaymentBooking.id == confirmation.payment_booking_id)
        )
        payment_booking = payment_booking_result.scalar_one()
        
        booking = payment_booking.booking
        student_id = confirmation.student_id
        teacher_id = confirmation.teacher_id
        
        # Obtener datos del estudiante
        student_result = await db.execute(
            select(User).where(User.id == student_id)
        )
        student = student_result.scalar_one()
        
        # Obtener datos del docente
        teacher_result = await db.execute(
            select(User).where(User.id == teacher_id)
        )
        teacher = teacher_result.scalar_one()
        
        # Preparar detalles del reembolso
        refund_details = {
            'class_date': booking.start_time.strftime('%d/%m/%Y %H:%M') + ' - ' + booking.end_time.strftime('%H:%M'),
            'teacher_name': f"{teacher.first_name} {teacher.last_name}",
            'amount': f"{refund_amount/100:.2f}",
            'reason': refund_reason,
            'processed_date': 'Hoy',
            'payment_method': 'Método original'
        }
        
        # Enviar notificación y email al estudiante
        await send_refund_processed_notification(db, student_id, refund_details)
        await send_refund_processed_email(db, student_id, refund_details)
        
        logger.info(f"✅ Notificaciones y emails de refund enviados para confirmación {confirmation.id}")
        
        return {
            "success": True,
            "notifications_sent": 1,
            "emails_sent": 1
        }
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificaciones de refund: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
