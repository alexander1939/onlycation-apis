from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from typing import Dict
import logging
from fastapi import HTTPException

from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.booking.confirmation import Confirmation
from app.models.booking.payment_bookings import PaymentBooking

logger = logging.getLogger(__name__)

async def reschedule_booking(
    db: AsyncSession,
    student_id: int,
    booking_id: int,
    new_availability_id: int,
    new_start_time: datetime,
    new_end_time: datetime
) -> Dict:
    """
    Reagenda una reserva existente a un nuevo horario disponible del docente
    """
    try:
        # Obtener la reserva actual con todas las relaciones
        query = select(Booking).options(
            selectinload(Booking.availability).selectinload(Availability.user),
            selectinload(Booking.user)
        ).where(
            Booking.id == booking_id,
            Booking.user_id == student_id
        )
        
        result = await db.execute(query)
        booking = result.scalar_one_or_none()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Reserva no encontrada o no pertenece al estudiante")
        
        # Validar que falten al menos 30 minutos para la clase actual
        current_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)  # Mexico time
        minutes_until_class = (booking.start_time - current_time).total_seconds() / 60
        
        # BLOQUEAR: Si la clase ya terminó
        if current_time >= booking.end_time:
            raise HTTPException(status_code=400, detail="No puedes reagendar una clase que ya terminó")
        
        # BLOQUEAR: Si la clase está en progreso (entre start_time y end_time)
        if current_time >= booking.start_time and current_time < booking.end_time:
            raise HTTPException(status_code=400, detail="No puedes reagendar durante la sesión de tutoría - la clase está en progreso")
        
        # BLOQUEAR: Si faltan 30 minutos o menos antes de la clase
        if minutes_until_class <= 30:
            raise HTTPException(status_code=400, detail=f"No puedes reagendar - faltan solo {int(minutes_until_class)} minutos para la clase (mínimo 30 minutos)")
        
        # Verificar que la nueva disponibilidad existe y pertenece al mismo docente
        new_availability_query = select(Availability).where(
            Availability.id == new_availability_id,
            Availability.user_id == booking.availability.user_id  # Mismo docente
        )
        
        new_availability_result = await db.execute(new_availability_query)
        new_availability = new_availability_result.scalar_one_or_none()
        
        if not new_availability:
            raise HTTPException(status_code=404, detail="La nueva disponibilidad no existe o no pertenece al mismo docente")
        
        # Validar que el nuevo horario esté dentro de la disponibilidad del docente
        if not (new_availability.start_time <= new_start_time and new_end_time <= new_availability.end_time):
            raise HTTPException(status_code=400, detail="El nuevo horario no está dentro de la disponibilidad del docente")
        
        # Verificar que no haya conflictos con otras reservas en el nuevo horario
        conflict_query = select(Booking).where(
            Booking.availability_id == new_availability_id,
            Booking.id != booking_id,  # Excluir la reserva actual
            Booking.start_time < new_end_time,
            Booking.end_time > new_start_time
        )
        
        conflict_result = await db.execute(conflict_query)
        conflicting_booking = conflict_result.scalar_one_or_none()
        
        if conflicting_booking:
            raise HTTPException(status_code=409, detail="Ya existe una reserva en el nuevo horario solicitado")
        
        # Actualizar la reserva
        booking.availability_id = new_availability_id
        booking.start_time = new_start_time
        booking.end_time = new_end_time
        booking.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(booking)
        
        logger.info(f"✅ Reserva {booking_id} reagendada exitosamente para el estudiante {student_id}")
        
        return {
            "booking_id": booking.id,
            "old_start_time": booking.start_time.isoformat(),
            "old_end_time": booking.end_time.isoformat(),
            "new_start_time": new_start_time.isoformat(),
            "new_end_time": new_end_time.isoformat(),
            "teacher_name": f"{booking.availability.user.first_name} {booking.availability.user.last_name}",
            "updated_at": booking.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error reagendando reserva {booking_id}: {str(e)}")
        await db.rollback()
        raise e

async def get_available_slots_for_teacher(
    db: AsyncSession,
    teacher_id: int,
    start_date: datetime,
    end_date: datetime
) -> Dict:
    """
    Obtiene los horarios disponibles de un docente para reagendar
    """
    try:
        # Obtener todas las disponibilidades del docente
        availability_query = select(Availability).where(
            Availability.user_id == teacher_id
        )
        
        availability_result = await db.execute(availability_query)
        availabilities = availability_result.scalars().all()
        
        # Obtener todas las reservas existentes del docente en el rango de fechas
        bookings_query = select(Booking).options(
            selectinload(Booking.availability)
        ).where(
            Booking.availability.has(Availability.user_id == teacher_id),
            Booking.start_time >= start_date,
            Booking.end_time <= end_date
        )
        
        bookings_result = await db.execute(bookings_query)
        existing_bookings = bookings_result.scalars().all()
        
        available_slots = []
        
        for availability in availabilities:
            # Verificar si hay conflictos con reservas existentes
            has_conflict = any(
                booking.start_time < availability.end_time and 
                booking.end_time > availability.start_time
                for booking in existing_bookings
                if booking.availability_id == availability.id
            )
            
            if not has_conflict:
                available_slots.append({
                    "availability_id": availability.id,
                    "day_of_week": availability.day_of_week,
                    "start_time": availability.start_time.isoformat(),
                    "end_time": availability.end_time.isoformat()
                })
        
        return {
            "success": True,
            "available_slots": available_slots
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo horarios disponibles del docente {teacher_id}: {str(e)}")
        return {
            "success": False,
            "message": f"Error obteniendo horarios disponibles: {str(e)}"
        }
