from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.refunds.refund_request import RefundRequest
from app.external.stripe_config import stripe
from app.services.utils.pagination_service import PaginationService
import logging
from app.services.refunds.refund_service import process_full_refund
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

async def validate_student_refund_request(
    db: AsyncSession,
    student_id: int,
    confirmation_id: int
) -> Dict:
    """
    Valida si un estudiante puede solicitar refund basado en las nuevas reglas de tiempo:
    1. Antes de la clase: Hasta 30 minutos antes del inicio
    2. Después de la clase: 4 horas después del fin para que docente confirme, si no confirma = refund automático
    """
    try:
        # Obtener confirmación con todos los datos
        query = select(Confirmation).options(
            selectinload(Confirmation.payment_booking).selectinload(PaymentBooking.booking),
            selectinload(Confirmation.teacher),
            selectinload(Confirmation.student)
        ).where(
            and_(
                Confirmation.id == confirmation_id,
                Confirmation.student_id == student_id  # Solo el estudiante puede solicitar su refund
            )
        )
        
        result = await db.execute(query)
        confirmation = result.scalar_one_or_none()
        
        if not confirmation:
            return {
                "eligible": False,
                "reason": "Confirmación no encontrada o no pertenece al estudiante",
                "confirmation_id": confirmation_id
            }
            
        payment_booking = confirmation.payment_booking
        booking = payment_booking.booking if payment_booking else None
        
        if not payment_booking or not booking:
            return {
                "eligible": False,
                "reason": "Datos de booking incompletos",
                "confirmation_id": confirmation_id
            }
            
        # Verificar si ya fue refunded
        if payment_booking.status_id == 4:
            return {
                "eligible": False,
                "reason": "Este booking ya fue reembolsado",
                "confirmation_id": confirmation_id
            }
        
        # Calcular tiempos y condiciones - usar timezone México (UTC-6)
        from datetime import timezone, timedelta
        mexico_tz = timezone(timedelta(hours=-6))
        current_time = datetime.now(mexico_tz).replace(tzinfo=None)
        
        # REGLA 1: 30 minutos antes de la clase
        minutes_until_class = (booking.start_time - current_time).total_seconds() / 60
        can_refund_before_class = minutes_until_class > 30
        
        # REGLA 2: Después de la clase (solo 4 horas para que docente confirme)
        hours_since_class_ended = (current_time - booking.end_time).total_seconds() / 3600
        class_ended = booking.end_time < current_time
        class_in_progress = current_time >= booking.start_time and current_time <= booking.end_time
        teacher_confirmation_window_expired = class_ended and hours_since_class_ended >= 4
        teacher_didnt_confirm = confirmation.confirmation_date_teacher != True
        can_refund_after_class = teacher_confirmation_window_expired and teacher_didnt_confirm
        
       
        
        # Validar si docente ya confirmó (solo bloquear si confirmó explícitamente)
        if confirmation.confirmation_date_teacher is True:
            return {
                "eligible": False,
                "reason": "El docente ya confirmó que dio la clase",
                "confirmation_id": confirmation_id,
                "teacher_confirmed": True
            }
        
        # BLOQUEAR: Si la clase está en progreso
        if class_in_progress:
            return {
                "eligible": False,
                "reason": "No puedes solicitar refund durante la clase.",
                "confirmation_id": confirmation_id
            }
        
        # BLOQUEAR: Si la clase ya terminó pero no han pasado 4 horas
        if class_ended and hours_since_class_ended < 4:
            return {
                "eligible": False,
                "reason": f"Debes esperar 4 horas después de que termine la clase para solicitar refund (faltan {4 - hours_since_class_ended:.1f} horas)",
                "confirmation_id": confirmation_id
            }
        
        # VALIDACIÓN SIMPLE: Solo permitir refund si faltan MÁS de 30 minutos
        if minutes_until_class > 30:
            return {
                "eligible": True,
                "reason": f"Puedes cancelar hasta 30 minutos antes de la clase (faltan {int(minutes_until_class)} minutos)",
                "confirmation_id": confirmation_id,
                "refund_amount": payment_booking.total_amount / 100,
                "refund_type": "before_class",
                "class_start_time": booking.start_time.isoformat(),
                "teacher_name": f"{confirmation.teacher.first_name} {confirmation.teacher.last_name}"
            }
            
        # CASO 2: Refund después de la clase (docente no confirmó en 4 horas)
        if can_refund_after_class:
            return {
                "eligible": True,
                "reason": "El docente no confirmó la clase en 4 horas - Refund disponible",
                "confirmation_id": confirmation_id,
                "refund_amount": payment_booking.total_amount / 100,
                "refund_type": "teacher_no_show",
                "class_start_time": booking.start_time.isoformat(),
                "class_end_time": booking.end_time.isoformat(),
                "teacher_name": f"{confirmation.teacher.first_name} {confirmation.teacher.last_name}"
            }
        
        
        # BLOQUEAR: Si faltan 30 minutos o menos antes de la clase
        elif minutes_until_class <= 30 and minutes_until_class > 0:
            return {
                "eligible": False,
                "reason": f"No puedes cancelar - faltan solo {int(minutes_until_class)} minutos (mínimo 30 minutos)",
                "confirmation_id": confirmation_id
            }
        
        # BLOQUEAR: Si la clase ya terminó y el estudiante no ha confirmado su asistencia
        elif class_ended and confirmation.confirmation_date_student is None:
            if hours_since_class_ended < 4:
                return {
                    "eligible": False,
                    "reason": "Debes confirmar tu asistencia dentro de las primeras 4 horas después de la clase para poder solicitar un refund",
                    "confirmation_id": confirmation_id
                }
            else:
                return {
                    "eligible": False,
                    "reason": "Ya no puedes solicitar refund - el plazo para confirmar tu asistencia (4 horas) ha expirado",
                    "confirmation_id": confirmation_id
                }
        
        # BLOQUEAR: Si el estudiante confirmó que NO asistió
        elif (class_ended and confirmation.confirmation_date_student is False):
            return {
                "eligible": False,
                "reason": "No puedes solicitar refund porque confirmaste que NO asististe a la clase",
                "confirmation_id": confirmation_id
            }
        
        # CASO ÚNICO: Estudiante SÍ asistió = REFUND disponible (independiente del docente)
        elif (class_ended and confirmation.confirmation_date_student is True):
            # Verificar ventana de 24 horas para solicitar refund después de confirmar
            if hours_since_class_ended <= 24:
                return {
                    "eligible": True,
                    "reason": "Confirmaste que asististe - Refund disponible por falta del docente",
                    "confirmation_id": confirmation_id,
                    "refund_amount": payment_booking.total_amount / 100,
                    "refund_type": "teacher_no_show",
                    "class_start_time": booking.start_time.isoformat(),
                    "class_end_time": booking.end_time.isoformat(),
                    "teacher_name": f"{confirmation.teacher.first_name} {confirmation.teacher.last_name}"
                }
            else:
                return {
                    "eligible": False,
                    "reason": "Ya no puedes solicitar refund - el plazo de 24 horas después de confirmar tu asistencia ha expirado",
                    "confirmation_id": confirmation_id
                }
        
        # CASO 6: Cualquier otro caso no elegible
        else:
            return {
                "eligible": False,
                "reason": "No elegible para refund en este momento",
                "confirmation_id": confirmation_id
            }
        
    except Exception as e:
        logger.error(f"❌ Error validando refund request: {str(e)}")
        return {
            "eligible": False,
            "reason": f"Error interno: {str(e)}",
            "confirmation_id": confirmation_id
        }

async def create_refund_request_record(
    db: AsyncSession,
    student_id: int,
    confirmation_id: int,
    validation: Dict
) -> RefundRequest:
    """
    Crea un registro de solicitud de refund en la base de datos
    """
    try:
        # Obtener datos de la confirmación
        query = select(Confirmation).options(
            selectinload(Confirmation.payment_booking).selectinload(PaymentBooking.booking)
        ).where(Confirmation.id == confirmation_id)
        
        result = await db.execute(query)
        confirmation = result.scalar_one_or_none()
        
        if not confirmation:
            raise Exception("Confirmación no encontrada")
            
        payment_booking = confirmation.payment_booking
        booking = payment_booking.booking
        
        # Crear registro de refund request
        refund_request = RefundRequest(
            student_id=student_id,
            payment_booking_id=payment_booking.id,
            booking_id=booking.id,
            confirmation_id=confirmation_id,
            refund_amount=validation["refund_amount"],
            refund_type=validation["refund_type"],
            reason=validation["reason"],
            status="pending"
        )
        
        db.add(refund_request)
        await db.commit()
        await db.refresh(refund_request)
        
        logger.info(f"✅ Registro de refund request creado: ID {refund_request.id}")
        return refund_request
        
    except Exception as e:
        logger.error(f"❌ Error creando registro de refund request: {str(e)}")
        await db.rollback()
        raise

async def process_student_refund_request(
    db: AsyncSession,
    student_id: int,
    confirmation_id: int
) -> Dict:
    """
    Procesa una solicitud de refund de un estudiante con las nuevas reglas de tiempo
    """
    try:
        
        # Validar elegibilidad con nuevas reglas de tiempo
        validation = await validate_student_refund_request(db, student_id, confirmation_id)
        
        if not validation["eligible"]:
            return {
                "success": False,
                "error": validation["reason"],
                "confirmation_id": confirmation_id,
                "validation_details": validation
            }
            
        # Crear registro en la base de datos
        refund_request = await create_refund_request_record(db, student_id, confirmation_id, validation)
        
        # Procesar refund automáticamente
        try:
            refund_result = await process_full_refund(
                db=db,
                confirmation_id=confirmation_id,
                admin_user_id=None  # Sistema automático, no requiere admin
            )
            
            # Actualizar estado del registro
            if refund_result["success"]:
                refund_request.status = "processed"
                refund_request.stripe_refund_id = refund_result.get("stripe_refund_id")
                refund_request.processed_at = datetime.utcnow()
                await db.commit()
                
        except Exception as e:
            # Marcar como fallido
            refund_request.status = "rejected"
            await db.commit()
            return {
                "success": False,
                "error": f"Error procesando refund: {str(e)}",
                "confirmation_id": confirmation_id,
                "refund_request_id": refund_request.id
            }
        
        if refund_result["success"]:
            logger.info(f"✅ Refund procesado para estudiante {student_id}: ${validation['refund_amount']} MXN")
            return {
                "success": True,
                "message": f"Reembolso de ${validation['refund_amount']} MXN procesado exitosamente",
                "refund_amount": validation["refund_amount"],
                "stripe_refund_id": refund_result.get("stripe_refund_id"),
                "confirmation_id": confirmation_id,
                "refund_request_id": refund_request.id,
                "estimated_refund_days": "5-10 días hábiles"
            }
        else:
            # Marcar como fallido
            refund_request.status = "rejected"
            await db.commit()
            return {
                "error": f"Error procesando refund: {refund_result.get('error', 'Error desconocido')}",
                "confirmation_id": confirmation_id,
                "refund_request_id": refund_request.id
            }
        
    except Exception as e:
        logger.error(f"❌ Error procesando refund request: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno del servidor: {str(e)}",
            "confirmation_id": confirmation_id
        }

async def handle_get_refund_requests(
    db: AsyncSession,
    student_id: int,
    offset: int = 0,
    limit: int = 6
) -> Dict:
    """
    Obtiene las solicitudes de refund del estudiante con paginación
    """
    try:
        
        # Obtener refund requests con datos de booking y confirmation
        query = select(RefundRequest).options(
            selectinload(RefundRequest.booking),
            selectinload(RefundRequest.confirmation)
        ).where(RefundRequest.student_id == student_id).limit(limit).offset(offset)
        
        result = await db.execute(query)
        refund_items = result.scalars().all()
        
        # Obtener total count
        total_query = select(RefundRequest).where(RefundRequest.student_id == student_id)
        total_result = await db.execute(total_query)
        total_count = len(total_result.scalars().all())
        
        # Formatear los datos para la respuesta
        refund_requests = []
        for refund in refund_items:
            # Obtener descripción de la confirmación como reason
            reason = refund.confirmation.description_student if refund.confirmation and refund.confirmation.description_student else "Sin descripción"
            
            refund_requests.append({
                "id": refund.id,
                "refund_amount": refund.refund_amount,
                "reason": reason,
                "booking_start_time": refund.booking.start_time.isoformat() if refund.booking and refund.booking.start_time else None,
                "booking_end_time": refund.booking.end_time.isoformat() if refund.booking and refund.booking.end_time else None,
                "created_at": refund.created_at.isoformat() if refund.created_at else None
            })
        
        # Calcular si hay más datos
        has_more = (offset + limit) < total_count
        
        return {
            "success": True,
            "refund_requests": refund_requests,
            "pagination": {
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "has_more": has_more
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo refund requests: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno del servidor: {str(e)}"
        }

async def mark_student_cancellation(db: AsyncSession, confirmation_id: int) -> bool:
    """
    Marca que el estudiante canceló la clase
    """
    try:
        query = select(Confirmation).where(Confirmation.id == confirmation_id)
        result = await db.execute(query)
        confirmation = result.scalar_one_or_none()
        
        if confirmation:
            confirmation.confirmation_date_student = False  # Estudiante cancela
            await db.commit()
            logger.info(f"✅ Marcada cancelación del estudiante para confirmación {confirmation_id}")
            return True
        else:
            logger.warning(f"⚠️ Confirmación {confirmation_id} no encontrada para marcar cancelación")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error marcando cancelación del estudiante: {str(e)}")
        await db.rollback()
        return False

async def get_student_refundable_bookings(db: AsyncSession, student_id: int) -> list:
    """
    Obtiene todas las reservas del estudiante que pueden ser reembolsadas
    
    REGLAS DE TIEMPO:
    1. Antes de la clase: Hasta 30 minutos antes del inicio
    2. Después de la clase: 4 horas después del fin para que docente confirme, si no confirma = refund automático
    """
    try:
        current_time = datetime.utcnow()
        
        query = select(Confirmation).options(
            selectinload(Confirmation.payment_booking).selectinload(PaymentBooking.booking),
            selectinload(Confirmation.teacher)
        ).join(PaymentBooking).join(Booking).where(
            and_(
                Confirmation.student_id == student_id,
                # No está ya refunded
                PaymentBooking.status_id != 4,
                # Estudiante no ha cancelado aún
                Confirmation.confirmation_date_student != False
            )
        )
        
        result = await db.execute(query)
        confirmations = result.scalars().all()
        
        refundable_bookings = []
        for confirmation in confirmations:
            booking = confirmation.payment_booking.booking
            
            # Calcular tiempos y condiciones
            minutes_until_class = (booking.start_time - current_time).total_seconds() / 60
            can_refund_before_class = minutes_until_class > 30
            
            class_ended = current_time > booking.end_time
            class_in_progress = current_time >= booking.start_time and current_time <= booking.end_time
            hours_since_class_ended = (current_time - booking.end_time).total_seconds() / 3600 if class_ended else 0
            
            teacher_confirmation_window_expired = class_ended and hours_since_class_ended >= 4
            teacher_didnt_confirm = confirmation.confirmation_date_teacher is not True  # null o False
            can_refund_after_class = teacher_confirmation_window_expired and teacher_didnt_confirm
            
            # Determinar elegibilidad y razón
            eligible = False
            reason = ""
            refund_type = ""
            
            if can_refund_before_class:
                eligible = True
                reason = f"Puedes cancelar hasta 30 minutos antes de la clase (faltan {int(minutes_until_class)} minutos)"
                refund_type = "before_class"
            elif can_refund_after_class:
                eligible = True
                reason = "El docente no confirmó la clase - Refund disponible"
                refund_type = "teacher_no_show"
            elif class_ended and hours_since_class_ended < 4:
                reason = f"El docente tiene 4 horas para confirmar la clase (faltan {4 - hours_since_class_ended:.1f} horas)"
            elif minutes_until_class <= 30 and minutes_until_class > 0:
                reason = f"Muy cerca de la clase para cancelar (faltan {int(minutes_until_class)} minutos, mínimo 30)"
            elif confirmation.confirmation_date_teacher == True:
                reason = "El docente ya confirmó que dio la clase"
            else:
                reason = "No elegible para refund en este momento"
            
            if eligible:
                refundable_bookings.append({
                    "confirmation_id": confirmation.id,
                    "teacher_name": f"{confirmation.teacher.first_name} {confirmation.teacher.last_name}",
                    "class_date": booking.start_time.isoformat(),
                    "class_end_date": booking.end_time.isoformat(),
                    "refund_amount": confirmation.payment_booking.total_amount / 100,
                    "refund_type": refund_type,
                    "reason": reason,
                    "minutes_until_class": int(minutes_until_class) if minutes_until_class > 0 else 0,
                    "hours_since_class_ended": round(hours_since_class_ended, 1) if class_ended else 0,
                    "booking_date": confirmation.payment_booking.created_at.isoformat(),
                    "teacher_confirmed": confirmation.confirmation_date_teacher == True
                })
                
        logger.info(f"📋 Estudiante {student_id} tiene {len(refundable_bookings)} reservas reembolsables")
        return refundable_bookings
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo bookings reembolsables: {str(e)}")
        return []

async def handle_student_refund_request(
    db: AsyncSession,
    student_id: int,
    confirmation_id: int
) -> dict:
    """
    Maneja la solicitud de refund de un estudiante - toda la lógica centralizada
    """
    try:
        result = await process_student_refund_request(db, student_id, confirmation_id)
        
        # Personalizar respuesta según el tipo de error
        if not result["success"]:
            error_msg = result['error']
            if "ya fue reembolsado" in error_msg or "already refunded" in error_msg:
                return {
                    "success": True,
                    "message": "✅ El reembolso ya fue procesado anteriormente",
                    "confirmation_id": confirmation_id,
                    "processed_automatically": True,
                    "note": "Este booking ya tiene un reembolso completado"
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Refund rechazado: {error_msg}",
                    "confirmation_id": confirmation_id,
                    "processed_automatically": False
                }
        
        # Éxito
        return {
            "success": True,
            "message": f"✅ {result['message']}",
            "refund_amount": result["refund_amount"],
            "confirmation_id": result["confirmation_id"],
            "stripe_refund_id": result.get("stripe_refund_id"),
            "refund_request_id": result.get("refund_request_id"),
            "estimated_refund_days": result["estimated_refund_days"],
            "processed_automatically": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error en handle_student_refund_request: {str(e)}")
        return {
            "success": False,
            "message": f"❌ Error interno del servidor: {str(e)}",
            "confirmation_id": confirmation_id,
            "processed_automatically": False
        }

async def handle_get_refundable_bookings(
    db: AsyncSession,
    student_id: int,
    offset: int = 0,
    limit: int = 6
) -> Dict:
    """
    Maneja la obtención de bookings reembolsables - toda la lógica centralizada
    """
    try:
        refundable_bookings = await get_student_refundable_bookings(db, student_id)
        
        # Aplicar paginación manualmente
        total_count = len(refundable_bookings)
        paginated_bookings = refundable_bookings[offset:offset + limit]
        has_more = (offset + limit) < total_count
        
        return {
            "success": True,
            "refundable_bookings": paginated_bookings,
            "pagination": {
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "has_more": has_more
            },
            "rules": {
                "before_class": "Puedes cancelar hasta 30 minutos antes de la clase",
                "after_class": "Puedes solicitar refund 4 horas después si el docente no confirma",
                "teacher_confirmation_window": "El docente tiene solo 4 horas para confirmar después de la clase"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en handle_get_refundable_bookings: {str(e)}")
        return {
            "success": False,
            "message": f"Error interno del servidor: {str(e)}",
            "refundable_bookings": [],
            "total_count": 0,
            "rules": {}
        }
