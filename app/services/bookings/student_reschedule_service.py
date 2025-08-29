from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from typing import Dict, List
import logging

from app.models.booking.reschedule_request import RescheduleRequest
from app.models.booking.bookings import Booking
from app.models.common.status import Status
from app.services.utils.pagination_service import PaginationService

logger = logging.getLogger(__name__)

async def get_student_reschedule_requests(
    db: AsyncSession, 
    student_id: int,
    offset: int = 0,
    limit: int = 6
) -> Dict:
    """
    Obtener todas las solicitudes de reagendado pendientes para el estudiante con paginación
    """
    try:
        # Obtener el ID del status 'pending'
        pending_status_result = await db.execute(select(Status).where(Status.name == "pending"))
        pending_status = pending_status_result.scalar_one_or_none()
        pending_status_id = pending_status.id if pending_status else None
        
        # Construir query base con filtros
        base_query = select(RescheduleRequest).where(
            RescheduleRequest.student_id == student_id,
            RescheduleRequest.status_id == pending_status_id if pending_status_id else RescheduleRequest.status == "pending",
            RescheduleRequest.expires_at > datetime.utcnow()
        )
        
        # Contar total de registros
        from sqlalchemy import func
        total_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # Obtener datos paginados con relaciones
        paginated_query = base_query.options(
            selectinload(RescheduleRequest.booking),
            selectinload(RescheduleRequest.teacher),
            selectinload(RescheduleRequest.status)
        ).order_by(RescheduleRequest.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(paginated_query)
        requests = result.scalars().all()
        
        formatted_requests = [
            {
                "id": req.id,
                "booking_id": req.booking_id,
                "teacher_name": f"{req.teacher.first_name} {req.teacher.last_name}",
                "current_start_time": req.current_start_time.isoformat(),
                "current_end_time": req.current_end_time.isoformat(),
                "new_start_time": req.new_start_time.isoformat(),
                "new_end_time": req.new_end_time.isoformat(),
                "reason": req.reason,
                "status": req.status.name if req.status else "pending",
                "created_at": req.created_at.isoformat(),
                "expires_at": req.expires_at.isoformat()
            }
            for req in requests
        ]
        
        # Calcular si hay más datos
        has_more = (offset + limit) < total_count
        
        return {
            "requests": formatted_requests,
            "total": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": has_more
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo solicitudes de reagendado para estudiante: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def respond_to_reschedule_request(
    db: AsyncSession,
    student_id: int,
    request_id: int,
    approved: bool,
    response_message: str = None
) -> Dict:
    """
    Responder a una solicitud de reagendado (aprobar o rechazar)
    """
    try:
        # 1. Obtener la solicitud de reagendado
        query = select(RescheduleRequest).options(
            selectinload(RescheduleRequest.booking),
            selectinload(RescheduleRequest.teacher)
        ).where(
            RescheduleRequest.id == request_id,
            RescheduleRequest.student_id == student_id
        )
        
        result = await db.execute(query)
        request = result.scalar_one_or_none()
        
        if not request:
            raise HTTPException(status_code=404, detail="Solicitud de reagendado no encontrada")
        
        # 2. Verificar que la solicitud esté pendiente
        pending_status_result = await db.execute(select(Status).where(Status.name == "pending"))
        pending_status = pending_status_result.scalar_one_or_none()
        
        if pending_status and request.status_id != pending_status.id:
            # Obtener el nombre del status actual
            current_status_result = await db.execute(select(Status).where(Status.id == request.status_id))
            current_status = current_status_result.scalar_one_or_none()
            status_name = current_status.name if current_status else "unknown"
            raise HTTPException(status_code=400, detail=f"Esta solicitud ya fue {status_name}")
        
        # 3. Verificar que no haya expirado
        if datetime.utcnow() > request.expires_at:
            # Obtener el ID del status 'expired' o crear uno si no existe
            expired_status_result = await db.execute(select(Status).where(Status.name == "expired"))
            expired_status = expired_status_result.scalar_one_or_none()
            if expired_status:
                request.status_id = expired_status.id
            else:
                request.status = "expired"  # Fallback
            await db.commit()
            raise HTTPException(status_code=400, detail="Esta solicitud de reagendado ya expiró")
        
        # 4. Si es aprobada, realizar el reagendado
        if approved:
            # Verificar que no haya conflictos en el nuevo horario (por si acaso)
            cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
            cancelled_status = cancelled_status_result.scalar_one_or_none()
            cancelled_status_id = cancelled_status.id if cancelled_status else None
            
            conflict_query = select(Booking).where(
                Booking.availability_id == request.new_availability_id,
                Booking.id != request.booking_id,
                Booking.start_time < request.new_end_time,
                Booking.end_time > request.new_start_time,
                Booking.status_id != cancelled_status_id if cancelled_status_id else True
            )
            
            conflict_result = await db.execute(conflict_query)
            conflicting_booking = conflict_result.scalar_one_or_none()
            
            if conflicting_booking:
                # Obtener el ID del status 'expired'
                expired_status_result = await db.execute(select(Status).where(Status.name == "expired"))
                expired_status = expired_status_result.scalar_one_or_none()
                if expired_status:
                    request.status_id = expired_status.id
                else:
                    request.status = "expired"  # Fallback
                request.student_response = "Conflicto detectado - horario ya no disponible"
                request.responded_at = datetime.utcnow()
                await db.commit()
                raise HTTPException(status_code=409, detail="El horario solicitado ya no está disponible")
            
            # Actualizar la reserva
            booking = request.booking
            booking.availability_id = request.new_availability_id
            booking.start_time = request.new_start_time
            booking.end_time = request.new_end_time
            booking.updated_at = datetime.utcnow()
            
            # Obtener el ID del status 'approved'
            approved_status_result = await db.execute(select(Status).where(Status.name == "approved"))
            approved_status = approved_status_result.scalar_one_or_none()
            if approved_status:
                request.status_id = approved_status.id
            else:
                request.status = "approved"  # Fallback
            logger.info(f"✅ Reagendado aprobado - Reserva {request.booking_id} actualizada")
        else:
            # Obtener el ID del status 'rejected' o usar fallback
            rejected_status_result = await db.execute(select(Status).where(Status.name == "rejected"))
            rejected_status = rejected_status_result.scalar_one_or_none()
            if rejected_status:
                request.status_id = rejected_status.id
            else:
                request.status = "rejected"  # Fallback
            logger.info(f"❌ Reagendado rechazado para reserva {request.booking_id}")
        
        # 5. Actualizar la solicitud
        request.student_response = response_message
        request.responded_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(request)
        
        # TODO: Enviar notificación al docente
        
        # Obtener el nombre del status actualizado
        final_status_result = await db.execute(select(Status).where(Status.id == request.status_id))
        final_status = final_status_result.scalar_one_or_none()
        status_name = final_status.name if final_status else ("approved" if approved else "rejected")
        
        return {
            "request_id": request.id,
            "booking_id": request.booking_id,
            "status": status_name,
            "teacher_name": f"{request.teacher.first_name} {request.teacher.last_name}",
            "new_start_time": request.new_start_time.isoformat() if approved else None,
            "message": "Reagendado aprobado exitosamente" if approved else "Reagendado rechazado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error respondiendo a solicitud de reagendado: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def expire_old_requests(db: AsyncSession):
    """
    Marcar como expiradas las solicitudes que pasaron su tiempo límite
    """
    try:
        # Obtener los IDs de los status
        pending_status_result = await db.execute(select(Status).where(Status.name == "pending"))
        pending_status = pending_status_result.scalar_one_or_none()
        expired_status_result = await db.execute(select(Status).where(Status.name == "expired"))
        expired_status = expired_status_result.scalar_one_or_none()
        
        query = select(RescheduleRequest).where(
            RescheduleRequest.status_id == pending_status.id if pending_status else RescheduleRequest.status == "pending",
            RescheduleRequest.expires_at < datetime.utcnow()
        )
        
        result = await db.execute(query)
        expired_requests = result.scalars().all()
        
        for request in expired_requests:
            if expired_status:
                request.status_id = expired_status.id
            else:
                request.status = "expired"  # Fallback
        
        if expired_requests:
            await db.commit()
            logger.info(f"✅ {len(expired_requests)} solicitudes de reagendado marcadas como expiradas")
        
    except Exception as e:
        logger.error(f"❌ Error expirando solicitudes: {str(e)}")
        await db.rollback()
