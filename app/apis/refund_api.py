from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.deps import get_db, auth_required
from app.services.refunds.student_refund_service import (
    handle_student_refund_request,
    handle_get_refundable_bookings,
    handle_get_refund_requests
)
from app.schemas.refunds import (
    RefundRequestSchema,
    RefundResponseSchema,
    RefundableBookingsResponseSchema
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/student/request-refund", dependencies=[Depends(auth_required)])
async def student_request_refund(
    refund_request: RefundRequestSchema,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(auth_required)
):
    """
    El estudiante solicita refund automático de su clase.
    Sistema valida reglas automáticamente:
    - Antes de la clase: Hasta 30 minutos antes del inicio
    - Después de la clase: 4 horas después del fin para que docente confirme, si no confirma = refund automático
    """
    user_id = payload.get("user_id")
    print(f"🎓 DEBUG: Estudiante {user_id} solicitando refund automático para confirmación {refund_request.confirmation_id}")
    
    result = await handle_student_refund_request(
        db=db,
        student_id=user_id,
        confirmation_id=refund_request.confirmation_id
    )
    
    return {
        "success": True,
        "message": "Refund request processed successfully",
        "data": result
    }


@router.get("/student/my-refundable-bookings", dependencies=[Depends(auth_required)])
async def get_my_refundable_bookings(
    offset: int = 0,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(auth_required)
):
    """
    Obtiene todas las clases del estudiante que pueden ser reembolsadas
    
    REGLAS DE TIEMPO:
    - Antes de la clase: Hasta 30 minutos antes del inicio
    - Después de la clase: 4 horas después del fin para que docente confirme, si no confirma = refund automático
    """
    user_id = payload.get("user_id")
    
    result = await handle_get_refundable_bookings(
        db=db,
        student_id=user_id,
        offset=offset,
        limit=limit
    )
    
    return {
        "success": True,
        "message": "Refundable bookings retrieved successfully",
        "data": result
    }


@router.get("/student/my-refund-requests", dependencies=[Depends(auth_required)])
async def get_my_refund_requests(
    offset: int = 0,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(auth_required)
):
    """
    Obtiene las solicitudes de refund ya realizadas por el estudiante (desde refund_requests table)
    Con paginación para manejar grandes cantidades de datos
    """
    user_id = payload.get("user_id")
    
    result = await handle_get_refund_requests(
        db=db,
        student_id=user_id,
        offset=offset,
        limit=limit
    )
    
    return {
        "success": True,
        "message": "Refund requests retrieved successfully",
        "data": result
    }
