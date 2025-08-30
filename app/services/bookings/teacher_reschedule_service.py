from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import logging

from app.models.booking.bookings import Booking
from app.models.booking.reschedule_request import RescheduleRequest
from app.models.teachers.availability import Availability
from app.models.common.status import Status
from app.models.users.user import User
from app.services.utils.pagination_service import PaginationService
from app.services.notifications.booking_notification_service import send_reschedule_request_notification

logger = logging.getLogger(__name__)

async def create_teacher_reschedule_request(
    db: AsyncSession,
    teacher_id: int,
    booking_id: int,
    new_availability_id: int,
    new_start_time: datetime,
    new_end_time: datetime,
    reason: str = None
) -> Dict:
    """
    Crear una solicitud de reagendado por parte del docente
    """
    try:
        # 1. Verificar que la reserva existe y pertenece al docente
        query = select(Booking).options(
            selectinload(Booking.availability).selectinload(Availability.user),
            selectinload(Booking.user)
        ).where(Booking.id == booking_id)
        
        result = await db.execute(query)
        booking = result.scalar_one_or_none()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")
        
        if booking.availability.user_id != teacher_id:
            raise HTTPException(status_code=403, detail="Esta reserva no pertenece a tu disponibilidad")
        
        # 2. Verificar que la reserva no esté cancelada
        cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
        cancelled_status = cancelled_status_result.scalar_one_or_none()
        
        if cancelled_status and booking.status_id == cancelled_status.id:
            raise HTTPException(status_code=400, detail="No puedes solicitar reagendar una reserva cancelada")
        
        # 3. Verificar que no haya una solicitud pendiente para esta reserva
        pending_status_result = await db.execute(select(Status).where(Status.name == "pending"))
        pending_status = pending_status_result.scalar_one_or_none()
        pending_status_id = pending_status.id if pending_status else None
        
        existing_request_query = select(RescheduleRequest).where(
            RescheduleRequest.booking_id == booking_id,
            RescheduleRequest.status_id == pending_status_id if pending_status_id else RescheduleRequest.status == "pending"
        )
        existing_request_result = await db.execute(existing_request_query)
        existing_request = existing_request_result.scalar_one_or_none()
        
        if existing_request:
            raise HTTPException(status_code=400, detail="Ya existe una solicitud de reagendado pendiente para esta reserva")
        
        # 4. Verificar que la nueva disponibilidad existe y pertenece al mismo docente
        new_availability_query = select(Availability).where(
            Availability.id == new_availability_id,
            Availability.user_id == teacher_id
        )
        new_availability_result = await db.execute(new_availability_query)
        new_availability = new_availability_result.scalar_one_or_none()
        
        if not new_availability:
            raise HTTPException(status_code=404, detail="La nueva disponibilidad no existe o no te pertenece")
        
        # 5. Verificar que el nuevo horario esté dentro de la disponibilidad
        if not (new_availability.start_time <= new_start_time and new_end_time <= new_availability.end_time):
            raise HTTPException(status_code=400, detail="El nuevo horario no está dentro de tu disponibilidad")
        
        # 6. Verificar que no haya conflictos con otras reservas en el nuevo horario
        conflict_query = select(Booking).where(
            Booking.availability_id == new_availability_id,
            Booking.id != booking_id,
            Booking.start_time < new_end_time,
            Booking.end_time > new_start_time,
            Booking.status_id != cancelled_status.id if cancelled_status else True
        )
        
        conflict_result = await db.execute(conflict_query)
        conflicting_booking = conflict_result.scalar_one_or_none()
        
        if conflicting_booking:
            raise HTTPException(status_code=409, detail="Ya existe una reserva en el nuevo horario solicitado")
        
        # 7. Verificar que la clase actual no haya comenzado
        current_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)  # Mexico time
        if current_time >= booking.start_time:
            raise HTTPException(status_code=400, detail="No puedes solicitar reagendar una clase que ya comenzó o terminó")
        
        # 8. Crear la solicitud de reagendado (expira en 24 horas)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        reschedule_request = RescheduleRequest(
            booking_id=booking_id,
            teacher_id=teacher_id,
            student_id=booking.user_id,
            current_availability_id=booking.availability_id,
            current_start_time=booking.start_time,
            current_end_time=booking.end_time,
            new_availability_id=new_availability_id,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            reason=reason,
            status_id=pending_status_id,
            expires_at=expires_at
        )
        
        db.add(reschedule_request)
        await db.commit()
        await db.refresh(reschedule_request)
        
        logger.info(f"✅ Solicitud de reagendado creada por docente {teacher_id} para reserva {booking_id}")
        
        # Obtener student_id antes del commit para evitar problemas de sesión
        student_id = booking.user_id
        
        # Enviar notificación al estudiante
        reschedule_details = {}
        await send_reschedule_request_notification(db, student_id, reschedule_details)
        
        return {
            "request_id": reschedule_request.id,
            "booking_id": booking_id,
            "student_name": f"{booking.user.first_name} {booking.user.last_name}",
            "current_time": booking.start_time.isoformat(),
            "new_time": new_start_time.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creando solicitud de reagendado: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def get_teacher_reschedule_requests(
    db: AsyncSession, 
    teacher_id: int,
    offset: int = 0,
    limit: int = 6
) -> Dict:
    """
    Obtener todas las solicitudes de reagendado del docente con paginación
    """
    try:
        # Usar el servicio de paginación con filtros
        filters = {"teacher_id": teacher_id}
        
        paginated_data = await PaginationService.get_paginated_data(
            db=db,
            model=RescheduleRequest,
            offset=offset,
            limit=limit,
            filters=filters
        )
        
        # Cargar relaciones para los items obtenidos
        if paginated_data["items"]:
            request_ids = [req.id for req in paginated_data["items"]]
            detailed_query = select(RescheduleRequest).options(
                selectinload(RescheduleRequest.booking),
                selectinload(RescheduleRequest.student),
                selectinload(RescheduleRequest.status)
            ).where(
                RescheduleRequest.id.in_(request_ids)
            ).order_by(RescheduleRequest.created_at.desc())
            
            result = await db.execute(detailed_query)
            detailed_requests = result.scalars().all()
            
            formatted_requests = [
                {
                    "id": req.id,
                    "booking_id": req.booking_id,
                    "student_name": f"{req.student.first_name} {req.student.last_name}",
                    "current_start_time": req.current_start_time.isoformat(),
                    "current_end_time": req.current_end_time.isoformat(),
                    "new_start_time": req.new_start_time.isoformat(),
                    "new_end_time": req.new_end_time.isoformat(),
                    "reason": req.reason,
                    "status": req.status.name if req.status else "unknown",
                    "student_response": req.student_response,
                    "created_at": req.created_at.isoformat(),
                    "expires_at": req.expires_at.isoformat(),
                    "responded_at": req.responded_at.isoformat() if req.responded_at else None
                }
                for req in detailed_requests
            ]
        else:
            formatted_requests = []
        
        return {
            "requests": formatted_requests,
            "total": paginated_data["total"],
            "offset": paginated_data["offset"],
            "limit": paginated_data["limit"],
            "has_more": paginated_data["has_more"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo solicitudes de reagendado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
