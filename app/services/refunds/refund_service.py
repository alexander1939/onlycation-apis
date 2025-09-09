from sqlalchemy.ext.asyncio import AsyncSession
from app.services.refunds.refund_detection_service import (
    detect_refund_needed_confirmations,
    get_confirmation_for_refund,
    check_refund_eligibility
)
from app.services.refunds.stripe_refund_service import (
    process_stripe_refund,
    reverse_stripe_transfer,
    get_stripe_refund_status
)
from app.services.refunds.refund_status_service import (
    update_payment_booking_refund_status,
    update_booking_status_after_refund,
    create_refund_record,
    check_refund_time_limits
)
from app.services.refunds.refund_notification_service import (
    send_refund_notifications
)
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

async def process_full_refund(
    db: AsyncSession,
    confirmation_id: int,
    admin_user_id: Optional[int] = None
) -> Dict:
    """
    Procesa un refund completo basado en una confirmación negada
    
    Args:
        confirmation_id: ID de la confirmación que requiere refund
        admin_user_id: ID del admin que procesa el refund (opcional)
    
    Returns:
        Dict con resultado del proceso
    """
    try:
        
        # 1. Obtener confirmación con todos los datos
        confirmation = await get_confirmation_for_refund(db, confirmation_id)
        if not confirmation:
            return {
                "success": False,
                "error": "Confirmación no encontrada",
                "confirmation_id": confirmation_id
            }
            
        # 2. Verificar elegibilidad para refund
        eligibility = await check_refund_eligibility(confirmation)
        if not eligibility["eligible"]:
            return {
                "success": False,
                "error": f"No elegible para refund: {eligibility['reason']}",
                "confirmation_id": confirmation_id
            }
            
        # 3. Sin restricciones de tiempo - permitir refund en cualquier momento
        time_check = {"allowed": True, "reason": "Sin restricciones de tiempo"}
            
        payment_booking = confirmation.payment_booking
        refund_amount = payment_booking.total_amount
        
        
        # 4. Procesar refund en Stripe
        refund_result = await process_stripe_refund(
            db=db,
            payment_booking=payment_booking,
            refund_amount=refund_amount,
            reason="requested_by_customer"
        )
        
        if not refund_result["success"]:
            return {
                "success": False,
                "error": f"Error en Stripe refund: {refund_result['error']}",
                "confirmation_id": confirmation_id
            }
            
        # 5. Revertir transferencia al docente si es necesario
        reversal_result = None
        if eligibility["teacher_reversal_needed"]:
            print(f"🔄 DEBUG: Revirtiendo transferencia al docente")
            reversal_result = await reverse_stripe_transfer(
                db=db,
                payment_booking=payment_booking,
                transfer_amount=payment_booking.teacher_amount
            )
            
            if not reversal_result["success"]:
                logger.warning(f"⚠️ Error revirtiendo transferencia: {reversal_result['error']}")
                # Continuar con el refund aunque falle la reversión
                
        # 6. Actualizar estados en base de datos
        status_updated = await update_payment_booking_refund_status(
            db=db,
            payment_booking_id=payment_booking.id,
            stripe_refund_id=refund_result["stripe_refund_id"],
            refund_amount=refund_amount,
            stripe_reversal_id=reversal_result["stripe_reversal_id"] if reversal_result else None
        )
        
        if not status_updated:
            logger.warning(f"⚠️ Error actualizando status de PaymentBooking {payment_booking.id}")
            
        # 7. Actualizar estado del booking
        booking_updated = await update_booking_status_after_refund(
            db=db,
            booking_id=payment_booking.booking_id
        )
        
        if not booking_updated:
            logger.warning(f"⚠️ Error actualizando status de Booking {payment_booking.booking_id}")
            
        # 8. Crear registro de refund para auditoría
        refund_data = {
            "stripe_refund_id": refund_result["stripe_refund_id"],
            "stripe_reversal_id": reversal_result["stripe_reversal_id"] if reversal_result else None,
            "refund_amount": refund_amount,
            "reversal_amount": payment_booking.teacher_amount if reversal_result else 0,
            "reason": eligibility["refund_type"],
            "processed_by": admin_user_id
        }
        
        await create_refund_record(db, payment_booking.id, refund_data)
        
        # 9. Enviar notificaciones
        await send_refund_notifications(
            db=db,
            confirmation=confirmation,
            refund_amount=refund_amount,
            refund_reason=eligibility["refund_type"]
        )
        
        logger.info(f"✅ Refund procesado exitosamente para confirmación {confirmation_id}")
        
        return {
            "success": True,
            "confirmation_id": confirmation_id,
            "refund_amount": refund_amount,
            "stripe_refund_id": refund_result["stripe_refund_id"],
            "stripe_reversal_id": reversal_result["stripe_reversal_id"] if reversal_result else None,
            "refund_type": eligibility["refund_type"],
            "message": f"Refund de ${refund_amount/100} MXN procesado exitosamente"
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando refund para confirmación {confirmation_id}: {str(e)}")
        await db.rollback()
        return {
            "success": False,
            "error": f"Error interno: {str(e)}",
            "confirmation_id": confirmation_id
        }

async def process_batch_refunds(db: AsyncSession, admin_user_id: int) -> Dict:
    """
    Procesa todos los refunds pendientes automáticamente
    """
    try:
        # Detectar confirmaciones que necesitan refund
        confirmations = await detect_refund_needed_confirmations(db)
        
        if not confirmations:
            return {
                "success": True,
                "processed": 0,
                "message": "No hay refunds pendientes"
            }
            
        results = []
        successful = 0
        failed = 0
        
        for confirmation in confirmations:
            result = await process_full_refund(db, confirmation.id, admin_user_id)
            results.append(result)
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
                
        logger.info(f"📊 Batch refunds: {successful} exitosos, {failed} fallidos")
        
        return {
            "success": True,
            "processed": len(confirmations),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Error en batch refunds: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }
