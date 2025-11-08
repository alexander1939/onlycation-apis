from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_
from datetime import datetime, timedelta, timezone, time as dt_time
from typing import Dict, List, Optional
import logging
from fastapi import HTTPException

from app.models.teachers.availability import Availability
from app.models.booking.bookings import Booking
from app.models.common.status import Status
from app.models.users.user import User

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
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

def generate_time_slots(availability: Availability, bookings: List[Booking]) -> List[Dict]:
    """
    Generar slots de tiempo por horas exactas para una disponibilidad
    """
    slots = []
    current_time = availability.start_time  # Ya es datetime
    end_time = availability.end_time  # Ya es datetime
    
    # Generar slots de 1 hora
    while current_time < end_time:
        slot_end = current_time + timedelta(hours=1)
        
        # Verificar si este slot está ocupado por alguna reserva
        is_occupied = False
        booking_status = None
        
        for booking in bookings:
            # Verificar si hay overlap entre el slot y la reserva
            if (booking.start_time < slot_end and 
                booking.end_time > current_time and
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
            "status": status,
            "availability_id": availability.id
        }
        
        slots.append(slot)
        current_time = slot_end
    
    return slots

def dt_time_to_datetime(time_obj):
    """
    Convertir time a datetime si es necesario
    Si ya es datetime, devolver tal cual
    """
    from datetime import time as dt_time
    
    if isinstance(time_obj, datetime):
        return time_obj
    elif isinstance(time_obj, dt_time):
        return datetime.combine(datetime.now().date(), time_obj)
    else:
        return time_obj

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
            (dt_time_to_datetime(av.end_time) - dt_time_to_datetime(av.start_time)).total_seconds() / 3600 
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
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def get_public_teacher_weekly_agenda(
    db: AsyncSession,
    teacher_id: int,
    week_start_date: Optional[str] = None
) -> Dict:
    """
    Obtener la agenda pública del docente (puede ser semanal o rango personalizado)
    
    week_start_date puede ser:
    - None: usa semana actual
    - 'YYYY-MM-DD': usa esa fecha como inicio de semana (lunes a domingo)
    - 'YYYY-MM-DD,YYYY-MM-DD': usa rango personalizado (start_date,end_date)
    """
    try:
        # Configurar fechas del rango
        if not week_start_date:
            # Usar semana actual
            current_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
            days_since_monday = current_date.weekday()
            week_start = current_date - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end_date = week_start + timedelta(days=6)
            num_days = 7
        elif ',' in week_start_date:
            # Rango personalizado: 'start_date,end_date'
            start_str, end_str = week_start_date.split(',')
            week_start = datetime.strptime(start_str.strip(), "%Y-%m-%d")
            week_end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
            num_days = (week_end_date - week_start).days + 1
        else:
            # Semana específica (lunes a domingo)
            week_start = datetime.strptime(week_start_date, "%Y-%m-%d")
            days_since_monday = week_start.weekday()
            week_start = week_start - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end_date = week_start + timedelta(days=6)
            num_days = 7
        
        # Verificar que el docente existe y cargar su rol
        teacher_query = select(User).options(
            selectinload(User.role)
        ).where(User.id == teacher_id)
        teacher_result = await db.execute(teacher_query)
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        role_name = teacher.role.name if teacher.role else "Sin rol"
        
        if not teacher.role or teacher.role.name != "teacher":
            raise HTTPException(status_code=403, detail=f"El usuario especificado no es un docente. Rol actual: {role_name}")
        
        # 1. Obtener TODAS las disponibilidades del docente (son recurrentes por día de semana)
        availability_query = select(Availability).options(
            selectinload(Availability.preference)
        ).where(
            Availability.user_id == teacher_id
        ).order_by(Availability.day_of_week, Availability.start_time)
        
        availability_result = await db.execute(availability_query)
        all_availabilities = availability_result.scalars().all()
        
        # 2. Obtener reservas ocupadas del docente en el rango de fechas específico
        # Solo incluir bookings con status activos (no cancelados, inactivos, etc.)
        booking_query = select(Booking).options(
            selectinload(Booking.availability),
            selectinload(Booking.status)
        ).join(Availability).join(Status).where(
            Availability.user_id == teacher_id,
            Booking.start_time >= week_start,
            Booking.start_time <= week_end_date + timedelta(days=1),
            Status.name.in_(["active", "approved", "paid", "occupied"])
        ).order_by(Booking.start_time)
        
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()
        
        
        # 3. Construir la agenda (días del rango especificado)
        days = []
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_date = week_start
        
        for i in range(num_days):  # Iterar sobre el número de días del rango
            # Mapear día de la semana (Python: 0=Monday, 1=Tuesday...)
            # Pero nuestro sistema usa 1=Monday, 2=Tuesday...
            python_weekday = current_date.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
            our_day_of_week = python_weekday + 1 if python_weekday < 6 else 7  # 1=Monday, 2=Tuesday, ..., 7=Sunday
                        
            # Filtrar disponibilidades para este día de la semana
            day_availabilities = [
                av for av in all_availabilities 
                if av.day_of_week == our_day_of_week
            ]
                        
            # Filtrar bookings para esta fecha específica
            day_bookings = [
                booking for booking in bookings 
                if booking.start_time.date() == current_date.date()
            ]
            
            
            # Generar slots de tiempo para este día
            day_slots = []
            for availability in day_availabilities:
                # Convertir strings de hora a datetime para este día específico
                start_time_obj = datetime.strptime(availability.start_time, "%H:%M:%S").time()
                end_time_obj = datetime.strptime(availability.end_time, "%H:%M:%S").time()
                
                # Crear datetime completo para este día
                slot_start = datetime.combine(current_date.date(), start_time_obj)
                slot_end = datetime.combine(current_date.date(), end_time_obj)
                
                # Verificar si este slot está ocupado por alguna reserva
                is_occupied = False
                booking_status = None
                
                for booking in day_bookings:
                    
                    # Verificar si hay overlap entre el slot y la reserva
                    if (booking.start_time < slot_end and 
                        booking.end_time > slot_start and
                        booking.availability_id == availability.id):
                        is_occupied = True
                        booking_status = booking.status.name if booking.status else "occupied"
                        break
                
                # Determinar el estado del slot
                if is_occupied:
                    status = "occupied" if booking_status in ["confirmed", "active", "approved", "paid"] else "pending"
                else:
                    status = "available"
                
                slot = {
                    "start_time": availability.start_time[:5],  # "09:00"
                    "end_time": availability.end_time[:5],      # "10:00"
                    "status": status,
                    "availability_id": availability.id
                }
                
                day_slots.append(slot)
            
            days.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_name": day_names[python_weekday],
                "slots": day_slots,
                "total_slots": len(day_slots),
                "available_slots": len([s for s in day_slots if s["status"] == "available"]),
                "occupied_slots": len([s for s in day_slots if s["status"] == "occupied"])
            })
            
            current_date += timedelta(days=1)
        
        return {
            "teacher_id": teacher_id,
            "teacher_name": f"{teacher.first_name} {teacher.last_name}",
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end_date.strftime("%Y-%m-%d"),
            "days": days,
            "summary": {
                "total_days": num_days,
                "days_with_availability": len([d for d in days if d["total_slots"] > 0]),
                "total_slots": sum(d["total_slots"] for d in days),
                "available_slots": sum(d["available_slots"] for d in days),
                "occupied_slots": sum(d["occupied_slots"] for d in days)
            }
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def create_teacher_availability(
    db: AsyncSession,
    user_data: dict,
    availability_data: dict
) -> Dict:
    """
    Crear nueva disponibilidad para el docente autenticado
    Acepta: day_of_week (Monday, Tuesday, etc. o número) y horas (09:00 o 2025-11-04T09:00:00)
    """
    try:
        teacher_id = user_data["user_id"]
        
        # Validar datos requeridos
        required_fields = ["preference_id", "day_of_week", "start_time", "end_time"]
        for field in required_fields:
            if field not in availability_data:
                await db.rollback()
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        # Convertir strings a datetime (soporta ambos formatos)
        from datetime import datetime, time as dt_time
        
        reference_date = datetime.today()
        
        # Parsear start_time (soporta "09:00" o "2025-11-04T09:00:00")
        try:
            start_time_str = availability_data["start_time"]
            end_time_str = availability_data["end_time"]
            
            # Convertir "24:00" a "00:00" (medianoche)
            if end_time_str == "24:00":
                end_time_str = "00:00"
            
            # Detectar si es formato ISO completo o solo hora
            if "T" in start_time_str or len(start_time_str) > 8:
                # Formato completo: "2025-11-04T09:00:00"
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            elif ":" in start_time_str:
                # Formato solo hora: "09:00"
                parts = start_time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                start_time = datetime.combine(reference_date, dt_time(hour=hour, minute=minute))
            else:
                raise ValueError("Formato inválido")
            
            # Mismo proceso para end_time
            if "T" in end_time_str or len(end_time_str) > 8:
                # Formato completo: "2025-11-04T15:00:00"
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            elif ":" in end_time_str:
                # Formato solo hora: "15:00"
                parts = end_time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                end_time = datetime.combine(reference_date, dt_time(hour=hour, minute=minute))
                
                # CASO ESPECIAL: Si end_time <= start_time, significa que cruza medianoche
                # Ejemplo: 23:00 - 00:00 (debe ser válido)
                if end_time <= start_time:
                    end_time = end_time + timedelta(days=1)
            else:
                raise ValueError("Formato inválido")
                
        except (ValueError, IndexError) as e:
            await db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"Formato de hora inválido. Use HH:MM (ej: 09:00) o ISO. Error: {str(e)}"
            )
        
        # Validar que start_time sea antes que end_time
        if start_time >= end_time:
            await db.rollback()
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
        
        # Validar que las horas sean exactas (sin minutos)
        if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
            await db.rollback()
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser una hora exacta (ej: 09:00, 10:00)")
        
        if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
            await db.rollback()
            raise HTTPException(status_code=400, detail="La hora de fin debe ser una hora exacta (ej: 10:00, 13:00)")
        
        # Convertir datetime a string para guardar (modelo usa String)
        start_time_str_db = start_time.strftime("%H:%M:%S")
        end_time_str_db = end_time.strftime("%H:%M:%S")
        
        # Crear nueva disponibilidad con strings
        new_availability = Availability(
            user_id=teacher_id,
            preference_id=availability_data["preference_id"],
            day_of_week=availability_data["day_of_week"],
            start_time=start_time_str_db,  # String: "09:00:00"
            end_time=end_time_str_db       # String: "10:00:00"
        )
        
        db.add(new_availability)
        await db.commit()
        await db.refresh(new_availability)
        
        return {
            "id": new_availability.id,
            "user_id": new_availability.user_id,
            "preference_id": new_availability.preference_id,
            "day_of_week": new_availability.day_of_week,
            "start_time": new_availability.start_time[:5],  # "09:00:00" -> "09:00"
            "end_time": new_availability.end_time[:5],      # "10:00:00" -> "10:00"
            "created_at": new_availability.created_at.isoformat()
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
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
            from datetime import time as dt_time
            start_time = dt_time.fromisoformat(availability_data["start_time"])
            end_time = dt_time.fromisoformat(availability_data["end_time"])
            
            # Validaciones de tiempo
            if start_time >= end_time:
                await db.rollback()
                raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")
            
            if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
                await db.rollback()
                raise HTTPException(status_code=400, detail="La hora de inicio debe ser una hora exacta")
            
            if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
                await db.rollback()
                raise HTTPException(status_code=400, detail="La hora de fin debe ser una hora exacta")
            
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
            "start_time": availability.start_time.strftime("%H:%M"),
            "end_time": availability.end_time.strftime("%H:%M"),
            "updated_at": availability.updated_at.isoformat()
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
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
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error eliminando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def get_teacher_availability_list(
    db: AsyncSession,
    user_data: dict
) -> Dict:
    """
    Obtener lista de disponibilidades del docente
    Muestra día de la semana, hora de inicio y hora de fin
    """
    try:
        teacher_id = user_data["user_id"]
        
        # Verificar que el usuario sea docente
        if user_data.get("role") != "teacher":
            raise HTTPException(status_code=403, detail="Solo los docentes pueden acceder a esta funcionalidad")
        
        # Obtener todas las disponibilidades del docente
        query = select(Availability).where(
            Availability.user_id == teacher_id
        ).order_by(Availability.day_of_week, Availability.start_time)
        
        result = await db.execute(query)
        availabilities = result.scalars().all()
        
        if not availabilities:
            return {
                "teacher_id": teacher_id,
                "total_availabilities": 0,
                "availabilities": []
            }
        
        # Mapeo de números a nombres de días (1-based: 1=Monday, 2=Tuesday, etc.)
        day_names = {
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday",
            0: "Monday"  # Por compatibilidad si alguien usa 0
        }
        
        # Formatear las disponibilidades
        availability_list = []
        for av in availabilities:
            # Si day_of_week es string, usarlo directamente; si es int, convertir
            if isinstance(av.day_of_week, int):
                day_name = day_names.get(av.day_of_week, str(av.day_of_week))
            else:
                day_name = av.day_of_week
            
            # Si start_time/end_time son strings, usarlos directamente
            # Si son datetime, extraer solo la hora
            if isinstance(av.start_time, str):
                start_time = av.start_time[:5]  # "09:00:00" -> "09:00"
            else:
                start_time = av.start_time.strftime("%H:%M")
            
            if isinstance(av.end_time, str):
                end_time = av.end_time[:5]  # "10:00:00" -> "10:00"
            else:
                end_time = av.end_time.strftime("%H:%M")
            
            availability_list.append({
                "id": av.id,
                "day_of_week": day_name,
                "start_time": start_time,
                "end_time": end_time,
                "preference_id": av.preference_id
            })
        
        return {
            "teacher_id": teacher_id,
            "total_availabilities": len(availability_list),
            "availabilities": availability_list
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")
