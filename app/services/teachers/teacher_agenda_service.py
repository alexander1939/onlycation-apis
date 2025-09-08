from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging
from fastapi import HTTPException

from app.models.teachers.availability import Availability
from app.models.booking.bookings import Booking
from app.models.common.status import Status
from app.models.users.user import User

logger = logging.getLogger(__name__)

async def get_teacher_weekly_agenda(
    db: AsyncSession,
    user_data: dict,
    week_start_date: Optional[datetime] = None
) -> Dict:
    """
    Obtener la agenda semanal del docente (lunes a domingo)
    """
    try:
        # Verificar que el usuario sea docente
        user_role = user_data.get("role")
        logger.info(f"🔍 Usuario con rol '{user_role}' accediendo a agenda")
        if user_role != "teacher":
            raise HTTPException(status_code=403, detail="Solo los docentes pueden acceder a esta funcionalidad")
        
        teacher_id = user_data["user_id"]
        
        # Configurar fechas de la semana (lunes a domingo)
        if not week_start_date:
            current_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)  # Mexico time
            # Encontrar el lunes de esta semana
            days_since_monday = current_date.weekday()
            week_start_date = current_date - timedelta(days=days_since_monday)
        
        week_start_date = week_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end_date = week_start_date + timedelta(days=6)  # Domingo
        
        # Verificar que el docente existe y cargar su rol
        teacher_query = select(User).options(
            selectinload(User.role)
        ).where(User.id == teacher_id)
        teacher_result = await db.execute(teacher_query)
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        # Debug: imprimir el rol del usuario
        role_name = teacher.role.name if teacher.role else "Sin rol"
        logger.info(f"🔍 Usuario {teacher_id} tiene rol: {role_name}")
        
        if not teacher.role or teacher.role.name != "teacher":
            raise HTTPException(status_code=403, detail=f"El usuario especificado no es un docente. Rol actual: {role_name}")
        
        # 1. Obtener disponibilidades del docente en el rango de fechas
        availability_query = select(Availability).options(
            selectinload(Availability.preference)
        ).where(
            Availability.user_id == teacher_id,
            Availability.start_time >= week_start_date,
            Availability.start_time <= week_end_date
        ).order_by(Availability.start_time)
        
        availability_result = await db.execute(availability_query)
        availabilities = availability_result.scalars().all()
        
        # 2. Obtener reservas ocupadas del docente en el rango de fechas
        # Solo incluir bookings con status activos (no cancelados, inactivos, etc.)
        booking_query = select(Booking).options(
            selectinload(Booking.availability),
            selectinload(Booking.status)
        ).join(Availability).join(Status).where(
            Availability.user_id == teacher_id,
            Booking.start_time >= week_start_date,
            Booking.start_time <= week_end_date,
            Status.name.in_(["active", "approved", "paid", "occupied"])
        ).order_by(Booking.start_time)
        
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()
        
        # 3. Construir la agenda semanal (lunes a domingo)
        days = []
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_date = week_start_date
        
        for i in range(7):  # 7 días de la semana
            date_str = current_date.strftime('%Y-%m-%d')
            daily_slots = []
            
            # Obtener disponibilidades del día actual
            day_availabilities = [
                av for av in availabilities 
                if av.start_time.date() == current_date.date()
            ]
            
            # Para cada disponibilidad del día, generar slots
            for availability in day_availabilities:
                slots = generate_time_slots(availability, bookings)
                daily_slots.extend(slots)
            
            # Ordenar slots por hora
            daily_slots.sort(key=lambda x: x['start_time'])
            
            days.append({
                "date": date_str,
                "day_name": day_names[i],
                "slots": daily_slots
            })
            
            current_date += timedelta(days=1)
        
        return {
            "teacher_id": teacher_id,
            "teacher_name": f"{teacher.first_name} {teacher.last_name}",
            "week_start": week_start_date.strftime('%Y-%m-%d'),
            "week_end": week_end_date.strftime('%Y-%m-%d'),
            "days": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo agenda del docente: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

def generate_time_slots(availability: Availability, bookings: List[Booking]) -> List[Dict]:
    """
    Generar slots de tiempo por horas exactas para una disponibilidad
    """
    slots = []
    current_time = availability.start_time.replace(minute=0, second=0, microsecond=0)
    end_time = availability.end_time
    
    # Generar slots de 1 hora
    while current_time < end_time:
        slot_end = current_time + timedelta(hours=1)
        
        # Verificar si este slot está ocupado por alguna reserva
        is_occupied = False
        booking_status = None
        
        for booking in bookings:
            # Verificar si hay overlap entre el slot y la reserva
            if (booking.start_time < slot_end and booking.end_time > current_time and
                booking.availability_id == availability.id):
                is_occupied = True
                booking_status = booking.status.name if booking.status else "occupied"
                break
        
        # Determinar el estado del slot
        if is_occupied:
            status = "occupied" if booking_status in ["confirmed", "active"] else "pending"
        else:
            status = "available"
        
        slot = {
            "start_time": current_time.strftime('%H:%M'),
            "end_time": slot_end.strftime('%H:%M'),
            "datetime_start": current_time.isoformat(),
            "datetime_end": slot_end.isoformat(),
            "status": status,
            "availability_id": availability.id,
            "duration_hours": 1
        }
        
        slots.append(slot)
        current_time = slot_end
    
    return slots

async def get_teacher_availability_summary(
    db: AsyncSession,
    user_data: dict,
    days_ahead: int = 30
) -> Dict:
    """
    Obtener resumen de disponibilidad del docente (para estadísticas)
    """
    try:
        # Verificar que el usuario sea docente
        if user_data.get("role") != "teacher":
            raise HTTPException(status_code=403, detail="Solo los docentes pueden acceder a esta funcionalidad")
        
        teacher_id = user_data["user_id"]
        
        start_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
        end_date = start_date + timedelta(days=days_ahead)
        
        # Contar disponibilidades totales
        availability_query = select(Availability).where(
            Availability.user_id == teacher_id,
            Availability.start_time >= start_date,
            Availability.start_time <= end_date
        )
        availability_result = await db.execute(availability_query)
        availabilities = availability_result.scalars().all()
        
        # Contar reservas ocupadas
        booking_query = select(Booking).join(Status).where(
            Booking.user_id == teacher_id,
            Booking.start_time >= start_date,
            Booking.start_time <= end_date,
            Status.name.in_(["active", "pending", "approved", "paid", "occupied"])
        )
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()
        
        # Calcular estadísticas
        total_hours_available = sum(
            (av.end_time - av.start_time).total_seconds() / 3600 
            for av in availabilities
        )
        
        total_hours_booked = sum(
            (booking.end_time - booking.start_time).total_seconds() / 3600 
            for booking in bookings
        )
        
        availability_percentage = (
            ((total_hours_available - total_hours_booked) / total_hours_available * 100)
            if total_hours_available > 0 else 0
        )
        
        return {
            "teacher_id": teacher_id,
            "teacher_name": f"{teacher.first_name} {teacher.last_name}" if teacher else "Docente",
            "period_days": days_ahead,
            "total_hours_available": round(total_hours_available, 1),
            "total_hours_booked": round(total_hours_booked, 1),
            "total_hours_free": round(total_hours_available - total_hours_booked, 1),
            "availability_percentage": round(availability_percentage, 1),
            "total_bookings": len(bookings)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo resumen de disponibilidad: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def get_public_teacher_weekly_agenda(
    db: AsyncSession,
    teacher_id: int,
    week_start_date: Optional[datetime] = None
) -> Dict:
    """
    Obtener la agenda semanal pública de cualquier docente (lunes a domingo)
    """
    try:
        # Configurar fechas de la semana (lunes a domingo)
        if not week_start_date:
            current_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)  # Mexico time
            # Encontrar el lunes de esta semana
            days_since_monday = current_date.weekday()
            week_start_date = current_date - timedelta(days=days_since_monday)
        
        week_start_date = week_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end_date = week_start_date + timedelta(days=6)  # Domingo
        
        # Verificar que el docente existe y cargar su rol
        teacher_query = select(User).options(
            selectinload(User.role)
        ).where(User.id == teacher_id)
        teacher_result = await db.execute(teacher_query)
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        # Debug: imprimir el rol del usuario
        role_name = teacher.role.name if teacher.role else "Sin rol"
        logger.info(f"🔍 Usuario {teacher_id} tiene rol: {role_name}")
        
        if not teacher.role or teacher.role.name != "teacher":
            raise HTTPException(status_code=403, detail=f"El usuario especificado no es un docente. Rol actual: {role_name}")
        
        # 1. Obtener disponibilidades del docente en el rango de fechas
        availability_query = select(Availability).options(
            selectinload(Availability.preference)
        ).where(
            Availability.user_id == teacher_id,
            Availability.start_time >= week_start_date,
            Availability.start_time <= week_end_date
        ).order_by(Availability.start_time)
        
        availability_result = await db.execute(availability_query)
        availabilities = availability_result.scalars().all()
        
        # 2. Obtener reservas ocupadas del docente en el rango de fechas
        # Solo incluir bookings con status activos (no cancelados, inactivos, etc.)
        booking_query = select(Booking).options(
            selectinload(Booking.availability),
            selectinload(Booking.status)
        ).join(Availability).join(Status).where(
            Availability.user_id == teacher_id,
            Booking.start_time >= week_start_date,
            Booking.start_time <= week_end_date,
            Status.name.in_(["active", "approved", "paid", "occupied"])
        ).order_by(Booking.start_time)
        
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()
        
        # 3. Construir la agenda semanal (lunes a domingo)
        days = []
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_date = week_start_date
        
        for i in range(7):  # 7 días de la semana
            day_availabilities = [
                av for av in availabilities 
                if av.start_time.date() == current_date.date()
            ]
            day_bookings = [
                booking for booking in bookings 
                if booking.start_time.date() == current_date.date()
            ]
            
            # Generar slots de tiempo para este día
            day_slots = []
            for availability in day_availabilities:
                slots = generate_time_slots(availability, day_bookings)
                day_slots.extend(slots)
            
            days.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_name": day_names[i],
                "slots": day_slots,
                "total_slots": len(day_slots),
                "available_slots": len([s for s in day_slots if s["status"] == "available"]),
                "occupied_slots": len([s for s in day_slots if s["status"] == "occupied"])
            })
            
            current_date += timedelta(days=1)
        
        return {
            "teacher_id": teacher_id,
            "teacher_name": f"{teacher.first_name} {teacher.last_name}",
            "week_start": week_start_date.strftime("%Y-%m-%d"),
            "week_end": week_end_date.strftime("%Y-%m-%d"),
            "days": days,
            "summary": {
                "total_days": 7,
                "days_with_availability": len([d for d in days if d["total_slots"] > 0]),
                "total_slots": sum(d["total_slots"] for d in days),
                "available_slots": sum(d["available_slots"] for d in days),
                "occupied_slots": sum(d["occupied_slots"] for d in days)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo agenda pública del docente: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def create_teacher_availability(
    db: AsyncSession,
    user_data: dict,
    availability_data: dict
) -> Dict:
    """
    Crear nueva disponibilidad para el docente autenticado
    """
    try:
        
        teacher_id = user_data["user_id"]
        
        # Validar datos requeridos
        required_fields = ["preference_id", "day_of_week", "start_time", "end_time"]
        for field in required_fields:
            if field not in availability_data:
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        # Convertir strings de fecha/hora a datetime
        from datetime import datetime
        start_time = datetime.fromisoformat(availability_data["start_time"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(availability_data["end_time"].replace("Z", "+00:00"))
        
        # Validar que start_time sea antes que end_time
        if start_time >= end_time:
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
        
        # Validar que start_time y end_time estén en la misma fecha
        if start_time.date() != end_time.date():
            raise HTTPException(status_code=400, detail="La hora de inicio y fin deben estar en la misma fecha")
        
        # Validar que las horas sean exactas (sin minutos ni segundos)
        if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser una hora exacta (ej: 10:00:00)")
        
        if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
            raise HTTPException(status_code=400, detail="La hora de fin debe ser una hora exacta (ej: 13:00:00)")
        
        # Verificar que no haya conflictos con disponibilidades existentes
        existing_query = select(Availability).where(
            Availability.user_id == teacher_id,
            Availability.day_of_week == availability_data["day_of_week"],
            Availability.start_time < end_time,
            Availability.end_time > start_time
        )
        existing_result = await db.execute(existing_query)
        existing_availability = existing_result.scalar_one_or_none()
        
        if existing_availability:
            raise HTTPException(
                status_code=409, 
                detail="Ya existe una disponibilidad que se superpone con este horario"
            )
        
        # Crear nueva disponibilidad
        new_availability = Availability(
            user_id=teacher_id,
            preference_id=availability_data["preference_id"],
            day_of_week=availability_data["day_of_week"],
            start_time=start_time,
            end_time=end_time
        )
        
        db.add(new_availability)
        await db.commit()
        await db.refresh(new_availability)
        
        return {
            "id": new_availability.id,
            "user_id": new_availability.user_id,
            "preference_id": new_availability.preference_id,
            "day_of_week": new_availability.day_of_week,
            "start_time": new_availability.start_time.isoformat(),
            "end_time": new_availability.end_time.isoformat(),
            "created_at": new_availability.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def update_teacher_availability(
    db: AsyncSession,
    user_data: dict,
    availability_id: int,
    availability_data: dict
) -> Dict:
    """
    Actualizar disponibilidad del docente autenticado
    """
    try:
        teacher_id = user_data["user_id"]
        
        # Verificar que la disponibilidad existe y pertenece al docente
        availability_query = select(Availability).where(
            Availability.id == availability_id,
            Availability.user_id == teacher_id
        )
        availability_result = await db.execute(availability_query)
        availability = availability_result.scalar_one_or_none()
        
        if not availability:
            raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
        
        # Verificar que no hay reservas activas en esta disponibilidad
        active_bookings_query = select(Booking).join(Status).where(
            Booking.availability_id == availability_id,
            Status.name.in_(["active", "approved", "paid", "occupied"])
        )
        active_bookings_result = await db.execute(active_bookings_query)
        active_bookings = active_bookings_result.scalars().all()
        
        if active_bookings:
            raise HTTPException(
                status_code=409, 
                detail="No se puede editar la disponibilidad porque tiene reservas activas"
            )
        
        # Validar y actualizar campos si se proporcionan
        if "start_time" in availability_data and "end_time" in availability_data:
            from datetime import datetime
            start_time = datetime.fromisoformat(availability_data["start_time"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(availability_data["end_time"].replace("Z", "+00:00"))
            
            # Validaciones de tiempo
            if start_time >= end_time:
                raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
            
            if start_time.date() != end_time.date():
                raise HTTPException(status_code=400, detail="La hora de inicio y fin deben estar en la misma fecha")
            
            if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
                raise HTTPException(status_code=400, detail="La hora de inicio debe ser una hora exacta")
            
            if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
                raise HTTPException(status_code=400, detail="La hora de fin debe ser una hora exacta")
            
            # Verificar conflictos con otras disponibilidades (excluyendo la actual)
            conflict_query = select(Availability).where(
                Availability.user_id == teacher_id,
                Availability.id != availability_id,  # Excluir la disponibilidad actual
                Availability.day_of_week == availability_data.get("day_of_week", availability.day_of_week),
                Availability.start_time < end_time,
                Availability.end_time > start_time
            )
            conflict_result = await db.execute(conflict_query)
            conflicting_availability = conflict_result.scalar_one_or_none()
            
            if conflicting_availability:
                raise HTTPException(
                    status_code=409, 
                    detail="Ya existe otra disponibilidad que se superpone con este horario"
                )
            
            availability.start_time = start_time
            availability.end_time = end_time
        
        if "preference_id" in availability_data:
            availability.preference_id = availability_data["preference_id"]
        
        if "day_of_week" in availability_data:
            availability.day_of_week = availability_data["day_of_week"]
        
        await db.commit()
        await db.refresh(availability)
        
        return {
            "id": availability.id,
            "user_id": availability.user_id,
            "preference_id": availability.preference_id,
            "day_of_week": availability.day_of_week,
            "start_time": availability.start_time.isoformat(),
            "end_time": availability.end_time.isoformat(),
            "updated_at": availability.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def delete_teacher_availability(
    db: AsyncSession,
    user_data: dict,
    availability_id: int
) -> None:
    """
    Eliminar disponibilidad del docente autenticado
    """
    try:
        teacher_id = user_data["user_id"]
        
        # Verificar que la disponibilidad existe y pertenece al docente
        availability_query = select(Availability).where(
            Availability.id == availability_id,
            Availability.user_id == teacher_id
        )
        availability_result = await db.execute(availability_query)
        availability = availability_result.scalar_one_or_none()
        
        if not availability:
            raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
        
        # Verificar que no hay reservas activas en esta disponibilidad
        active_bookings_query = select(Booking).join(Status).where(
            Booking.availability_id == availability_id,
            Status.name.in_(["active", "approved", "paid", "occupied"])
        )
        active_bookings_result = await db.execute(active_bookings_query)
        active_bookings = active_bookings_result.scalars().all()
        
        if active_bookings:
            raise HTTPException(
                status_code=409, 
                detail="No se puede eliminar la disponibilidad porque tiene reservas activas"
            )
        
        await db.delete(availability)
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
