from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.booking.bookings import Booking
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

async def update_payment_booking_refund_status(
    db: AsyncSession,
    payment_booking_id: int,
    stripe_refund_id: str,
    refund_amount: int,
    stripe_reversal_id: Optional[str] = None
) -> bool:
    """
    Actualiza el estado del PaymentBooking después de un refund exitoso
    """
    try:
        # Actualizar PaymentBooking
        update_data = {
            "status_id": 3,  # Asumiendo 4 = refunded
            "updated_at": datetime.utcnow()
        }
        
        # Si hubo reversal de transferencia, actualizar transfer_status
        if stripe_reversal_id:
            update_data["transfer_status"] = "reversed"
            
        query = update(PaymentBooking).where(
            PaymentBooking.id == payment_booking_id
        ).values(**update_data)
        
        await db.execute(query)
        await db.commit()
        
        logger.info(f"✅ PaymentBooking {payment_booking_id} actualizado a status refunded")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error actualizando PaymentBooking {payment_booking_id}: {str(e)}")
        await db.rollback()
        return False

async def update_booking_status_after_refund(
    db: AsyncSession,
    booking_id: int
) -> bool:
    """
    Actualiza el estado del Booking después de un refund
    """
    try:
        # Buscar el status 'cancelled' en la base de datos
        from app.models.common.status import Status
        status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
        cancelled_status = status_result.scalar_one_or_none()
        
        if not cancelled_status:
            logger.error("❌ Status 'cancelled' no encontrado en la base de datos")
            return False
            
        query = update(Booking).where(
            Booking.id == booking_id
        ).values(
            status_id=cancelled_status.id,  # Usar el ID correcto del status cancelled
            updated_at=datetime.utcnow()
        )
        
        await db.execute(query)
        await db.commit()
        
        logger.info(f"✅ Booking {booking_id} actualizado a status cancelled")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error actualizando Booking {booking_id}: {str(e)}")
        await db.rollback()
        return False

async def create_refund_record(
    db: AsyncSession,
    payment_booking_id: int,
    refund_data: Dict
) -> bool:
    """
    Crea un registro de refund para auditoría
    Nota: Esto requeriría crear una tabla RefundRecord si no existe
    """
    try:
        # Por ahora solo loggeamos, pero se podría crear una tabla de refunds
        refund_info = {
            "payment_booking_id": payment_booking_id,
            "stripe_refund_id": refund_data.get("stripe_refund_id"),
            "stripe_reversal_id": refund_data.get("stripe_reversal_id"),
            "refund_amount": refund_data.get("refund_amount"),
            "reversal_amount": refund_data.get("reversal_amount"),
            "refund_reason": refund_data.get("reason"),
            "processed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"📝 Refund record: {refund_info}")
        
        # TODO: Si se crea tabla RefundRecord, insertar aquí
        # refund_record = RefundRecord(**refund_info)
        # db.add(refund_record)
        # await db.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando refund record: {str(e)}")
        return False

async def get_refund_history(
    db: AsyncSession,
    payment_booking_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> list:
    """
    Obtiene historial de refunds
    """
    try:
        # Por ahora retornamos PaymentBookings con status refunded
        query = select(PaymentBooking).where(PaymentBooking.status_id == 4)
        
        if payment_booking_id:
            query = query.where(PaymentBooking.id == payment_booking_id)
            
        if user_id:
            query = query.where(PaymentBooking.user_id == user_id)
            
        result = await db.execute(query)
        refunded_payments = result.scalars().all()
        
        logger.info(f"📊 Encontrados {len(refunded_payments)} refunds")
        return refunded_payments
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial de refunds: {str(e)}")
        return []

async def check_refund_time_limits(confirmation: Confirmation) -> Dict:
    """
    Verifica si el refund está dentro de los límites de tiempo permitidos
    """
    try:
        booking = confirmation.payment_booking.booking if confirmation.payment_booking else None
        
        if not booking:
            return {"allowed": False, "reason": "Booking no encontrado"}
            
        # Ejemplo: permitir refund hasta 24 horas antes de la clase
        from datetime import timedelta
        refund_deadline = booking.start_time - timedelta(hours=24)
        current_time = datetime.utcnow()
        
        if current_time > refund_deadline:
            return {
                "allowed": False, 
                "reason": f"Refund no permitido. Deadline: {refund_deadline.isoformat()}"
            }
            
        return {
            "allowed": True,
            "deadline": refund_deadline.isoformat(),
            "hours_remaining": (refund_deadline - current_time).total_seconds() / 3600
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando límites de tiempo: {str(e)}")
        return {"allowed": False, "reason": f"Error: {str(e)}"}
