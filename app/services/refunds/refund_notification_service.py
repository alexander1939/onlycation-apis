from sqlalchemy.ext.asyncio import AsyncSession
from app.models.booking.confirmation import Confirmation
from app.services.notifications.notification_service import create_notification
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
        booking = confirmation.booking
        student = booking.user
        teacher = booking.availability.user
        
        # Notificación al estudiante
        student_message = f"Tu refund de ${refund_amount/100} MXN ha sido procesado. Razón: {refund_reason}"
        await create_notification(
            db=db,
            user_id=student.id,
            title="Refund Procesado",
            message=student_message,
            notification_type="refund_processed"
        )
        
        # Notificación al docente
        teacher_message = f"Se procesó un refund para tu clase con {student.first_name}. Monto: ${refund_amount/100} MXN"
        await create_notification(
            db=db,
            user_id=teacher.id,
            title="Refund de Clase",
            message=teacher_message,
            notification_type="refund_teacher"
        )
        
        logger.info(f"✅ Notificaciones de refund enviadas para confirmación {confirmation.id}")
        
        return {
            "success": True,
            "notifications_sent": 2
        }
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificaciones de refund: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
