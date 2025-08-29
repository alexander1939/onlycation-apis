from sqlalchemy.ext.asyncio import AsyncSession
from app.external.stripe_config import stripe
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

async def process_stripe_refund(
    db: AsyncSession, 
    payment_booking: PaymentBooking, 
    refund_amount: int,
    reason: str = "requested_by_customer"
) -> Dict:
    """
    Procesa un refund en Stripe usando el payment_intent_id
    
    Args:
        payment_booking: PaymentBooking con stripe_payment_intent_id
        refund_amount: Cantidad en centavos a reembolsar
        reason: Razón del refund para Stripe
    
    Returns:
        Dict con resultado del refund
    """
    try:
        if not payment_booking.stripe_payment_intent_id:
            return {
                "success": False,
                "error": "No hay payment_intent_id para procesar refund",
                "stripe_refund_id": None
            }
            
        print(f"💰 DEBUG: Procesando refund de ${refund_amount/100} MXN para payment_intent: {payment_booking.stripe_payment_intent_id}")
        
        # Crear refund en Stripe
        refund = stripe.Refund.create(
            payment_intent=payment_booking.stripe_payment_intent_id,
            amount=refund_amount,
            reason=reason,
            metadata={
                "payment_booking_id": str(payment_booking.id),
                "booking_id": str(payment_booking.booking_id),
                "user_id": str(payment_booking.user_id),
                "refund_type": "confirmation_denied"
            }
        )
        
        logger.info(f"✅ Refund creado en Stripe: {refund.id} por ${refund_amount/100} MXN")
        
        return {
            "success": True,
            "stripe_refund_id": refund.id,
            "amount": refund.amount,
            "status": refund.status,
            "error": None
        }
        
    except stripe.error.InvalidRequestError as e:
        logger.error(f"❌ Error de Stripe - Request inválido: {str(e)}")
        return {
            "success": False,
            "error": f"Request inválido: {str(e)}",
            "stripe_refund_id": None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Error de Stripe: {str(e)}")
        return {
            "success": False,
            "error": f"Error de Stripe: {str(e)}",
            "stripe_refund_id": None
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando refund: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}",
            "stripe_refund_id": None
        }

async def reverse_stripe_transfer(
    db: AsyncSession,
    payment_booking: PaymentBooking,
    transfer_amount: int
) -> Dict:
    """
    Revierte una transferencia ya realizada al docente en Stripe Connect
    
    Args:
        payment_booking: PaymentBooking con stripe_transfer_id
        transfer_amount: Cantidad a revertir (teacher_amount)
    
    Returns:
        Dict con resultado de la reversión
    """
    try:
        if not payment_booking.stripe_transfer_id:
            return {
                "success": False,
                "error": "No hay transfer_id para revertir",
                "stripe_reversal_id": None
            }
            
        if payment_booking.transfer_status != "transferred":
            return {
                "success": False,
                "error": f"Transfer status es '{payment_booking.transfer_status}', no se puede revertir",
                "stripe_reversal_id": None
            }
            
        print(f"🔄 DEBUG: Revirtiendo transferencia de ${transfer_amount/100} MXN, transfer_id: {payment_booking.stripe_transfer_id}")
        
        # Crear transfer reversal en Stripe
        reversal = stripe.Transfer.create_reversal(
            payment_booking.stripe_transfer_id,
            amount=transfer_amount,
            metadata={
                "payment_booking_id": str(payment_booking.id),
                "teacher_id": str(payment_booking.booking.teacher_id) if payment_booking.booking else "unknown",
                "reversal_reason": "confirmation_denied"
            }
        )
        
        logger.info(f"✅ Transfer reversal creado: {reversal.id} por ${transfer_amount/100} MXN")
        
        return {
            "success": True,
            "stripe_reversal_id": reversal.id,
            "amount": reversal.amount,
            "status": reversal.status,
            "error": None
        }
        
    except stripe.error.InvalidRequestError as e:
        logger.error(f"❌ Error de Stripe - Transfer reversal inválido: {str(e)}")
        return {
            "success": False,
            "error": f"Transfer reversal inválido: {str(e)}",
            "stripe_reversal_id": None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Error de Stripe en reversal: {str(e)}")
        return {
            "success": False,
            "error": f"Error de Stripe: {str(e)}",
            "stripe_reversal_id": None
        }
        
    except Exception as e:
        logger.error(f"❌ Error revirtiendo transfer: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}",
            "stripe_reversal_id": None
        }

async def get_stripe_refund_status(stripe_refund_id: str) -> Dict:
    """
    Obtiene el status actual de un refund en Stripe
    """
    try:
        refund = stripe.Refund.retrieve(stripe_refund_id)
        
        return {
            "success": True,
            "refund_id": refund.id,
            "status": refund.status,
            "amount": refund.amount,
            "currency": refund.currency,
            "created": refund.created,
            "error": None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Error obteniendo status de refund {stripe_refund_id}: {str(e)}")
        return {
            "success": False,
            "error": f"Error de Stripe: {str(e)}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo refund status: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }
