from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models.booking.confirmation import Confirmation
from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.common.status import Status
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

async def detect_refund_needed_confirmations(db: AsyncSession) -> List[Confirmation]:
    """
    Detecta confirmaciones que necesitan refund automático
    - Confirmaciones negadas por docente
    - Confirmaciones expiradas sin respuesta
    """
    try:
        # Obtener status "denied" y "expired"
        denied_status = await db.execute(select(Status).where(Status.name == "denied"))
        denied_status = denied_status.scalar_one_or_none()
        
        expired_status = await db.execute(select(Status).where(Status.name == "expired"))
        expired_status = expired_status.scalar_one_or_none()
        
        if not denied_status or not expired_status:
            logger.warning("⚠️ No se encontraron status 'denied' o 'expired'")
            return []
        
        # Buscar confirmaciones que necesitan refund
        result = await db.execute(
            select(Confirmation)
            .options(
                joinedload(Confirmation.booking).joinedload(Booking.payment_booking),
                joinedload(Confirmation.status)
            )
            .where(
                Confirmation.status_id.in_([denied_status.id, expired_status.id])
            )
        )
        
        confirmations = result.scalars().all()
        
        # Filtrar solo las que no han sido procesadas para refund
        refund_needed = []
        for confirmation in confirmations:
            if confirmation.booking and confirmation.booking.payment_booking:
                payment_booking = confirmation.booking.payment_booking
                # Solo procesar si no tiene refund_status o está pendiente
                if not hasattr(payment_booking, 'refund_status') or payment_booking.refund_status != "processed":
                    refund_needed.append(confirmation)
        
        logger.info(f"🔍 Detectadas {len(refund_needed)} confirmaciones que necesitan refund")
        return refund_needed
        
    except Exception as e:
        logger.error(f"❌ Error detectando confirmaciones para refund: {str(e)}")
        return []

async def get_confirmation_for_refund(db: AsyncSession, confirmation_id: int) -> Optional[Confirmation]:
    """
    Obtiene una confirmación con todos los datos necesarios para refund
    """
    try:
        result = await db.execute(
            select(Confirmation)
            .options(
                joinedload(Confirmation.payment_booking)
                .joinedload(PaymentBooking.booking)
                .joinedload(Booking.availability),
                joinedload(Confirmation.payment_booking)
                .joinedload(PaymentBooking.booking)
                .joinedload(Booking.user),
                joinedload(Confirmation.teacher),
                joinedload(Confirmation.student)
            )
            .where(Confirmation.id == confirmation_id)
        )
        
        confirmation = result.scalar_one_or_none()
        
        if not confirmation:
            logger.warning(f"⚠️ Confirmación {confirmation_id} no encontrada")
            return None
            
        if not confirmation.payment_booking:
            logger.warning(f"⚠️ Confirmación {confirmation_id} sin payment_booking asociado")
            return None
            
        if not confirmation.payment_booking.booking:
            logger.warning(f"⚠️ Confirmación {confirmation_id} sin booking asociado")
            return None
            
        return confirmation
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo confirmación {confirmation_id}: {str(e)}")
        return None

async def check_refund_eligibility(confirmation: Confirmation) -> Dict:
    """
    Verifica si una confirmación es elegible para refund
    """
    try:
        # Para confirmaciones donde docente dijo NO y estudiante dijo SÍ
        teacher_denied = confirmation.confirmation_date_teacher == False
        student_confirmed = confirmation.confirmation_date_student == True
        
        print(f"🔍 DEBUG: Valores de confirmación - Teacher: {confirmation.confirmation_date_teacher}, Student: {confirmation.confirmation_date_student}")
        print(f"🔍 DEBUG: teacher_denied: {teacher_denied}, student_confirmed: {student_confirmed}")
        
        booking = confirmation.payment_booking.booking
        payment_booking = confirmation.payment_booking
        
        # Verificar si ya fue procesado
        if hasattr(payment_booking, 'refund_status') and payment_booking.refund_status == "processed":
            return {
                "eligible": False,
                "reason": "Refund ya fue procesado anteriormente",
                "refund_type": None,
                "teacher_reversal_needed": False
            }
        
        # CASO 1: Docente negó la confirmación (teacher_denied = False, student_confirmed = True)
        if teacher_denied and student_confirmed:
            print(f"🔍 DEBUG: CASO 1 - Docente negó (False) y estudiante confirmó (True)")
            return {
                "eligible": True,
                "reason": "Docente negó la confirmación - Refund automático",
                "refund_type": "teacher_denied",
                "teacher_reversal_needed": False  # No se transfirió dinero al docente
            }
        
        # CASO 2: Docente no respondió (ambos None o solo student confirmó)
        if confirmation.confirmation_date_teacher is None and student_confirmed:
            return {
                "eligible": True,
                "reason": "Docente no respondió en tiempo límite",
                "refund_type": "teacher_no_response", 
                "teacher_reversal_needed": False
            }
        
        # CASO 3: Ninguno confirmó (clase abandonada)
        if confirmation.confirmation_date_teacher is None and confirmation.confirmation_date_student is None:
            return {
                "eligible": True,
                "reason": "Clase sin confirmación de ninguna parte",
                "refund_type": "no_confirmation",
                "teacher_reversal_needed": False
            }
        
        # Otros casos no elegibles
        return {
            "eligible": False,
            "reason": f"Confirmación no requiere refund automático (teacher: {confirmation.confirmation_date_teacher}, student: {confirmation.confirmation_date_student})",
            "refund_type": None,
            "teacher_reversal_needed": False
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando elegibilidad de refund: {str(e)}")
        return {
            "eligible": False,
            "reason": f"Error interno: {str(e)}",
            "refund_type": None,
            "teacher_reversal_needed": False
        }

async def check_student_refund_eligibility(
    db: AsyncSession, 
    student_id: int, 
    confirmation_id: int
) -> Dict:
    """
    Verifica si un estudiante puede solicitar refund de su reserva
    Reglas:
    - Solo dentro de 24h después de hacer la reserva
    - La clase no debe haber ocurrido
    - El docente no debe haber confirmado
    """
    try:
        # Obtener confirmación con datos completos
        confirmation = await get_confirmation_for_refund(db, confirmation_id)
        
        if not confirmation:
            return {
                "eligible": False,
                "reason": "Confirmación no encontrada",
                "refund_amount": 0
            }
        
        booking = confirmation.booking
        payment_booking = booking.payment_booking
        
        # Verificar que es del estudiante correcto
        if booking.user_id != student_id:
            return {
                "eligible": False,
                "reason": "Esta reserva no pertenece al usuario",
                "refund_amount": 0
            }
        
        # Verificar si ya fue procesado
        if hasattr(payment_booking, 'refund_status') and payment_booking.refund_status == "processed":
            return {
                "eligible": False,
                "reason": "Refund ya fue procesado anteriormente",
                "refund_amount": 0
            }
        
        # Verificar ventana de 24 horas desde la reserva
        booking_time = payment_booking.created_at
        current_time = datetime.utcnow()
        hours_since_booking = (current_time - booking_time).total_seconds() / 3600
        
        if hours_since_booking > 24:
            return {
                "eligible": False,
                "reason": f"Solo puedes cancelar dentro de 24 horas. Han pasado {hours_since_booking:.1f} horas",
                "refund_amount": 0,
                "hours_remaining_to_cancel": 0
            }
        
        # Verificar que la clase no haya ocurrido
        class_start_time = booking.start_time
        if current_time >= class_start_time:
            return {
                "eligible": False,
                "reason": "No puedes cancelar una clase que ya ocurrió o está en curso",
                "refund_amount": 0
            }
        
        # Verificar que el docente no haya confirmado
        if confirmation.status.name.lower() == "confirmed":
            return {
                "eligible": False,
                "reason": "No puedes cancelar una clase que ya fue confirmada por el docente",
                "refund_amount": 0
            }
        
        # Calcular información adicional
        hours_remaining_to_cancel = 24 - hours_since_booking
        hours_until_class = (class_start_time - current_time).total_seconds() / 3600
        
        return {
            "eligible": True,
            "reason": "Elegible para refund automático",
            "refund_amount": payment_booking.total_amount,
            "hours_remaining_to_cancel": max(0, hours_remaining_to_cancel),
            "hours_until_class": max(0, hours_until_class),
            "teacher_name": f"{booking.availability.user.first_name} {booking.availability.user.last_name}",
            "class_start_time": class_start_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando elegibilidad estudiante: {str(e)}")
        return {
            "eligible": False,
            "reason": f"Error interno: {str(e)}",
            "refund_amount": 0
        }
