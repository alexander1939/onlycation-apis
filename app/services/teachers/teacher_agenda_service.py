from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, extract, cast, Time, func, case, Integer
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
        user_role = user_data.get("role")
        if user_role != "teacher":
            raise HTTPException(status_code=403, detail="Solo los docentes pueden acceder a esta funcionalidad")
        
        teacher_id = user_data["user_id"]
        
        # Lógica de fechas unificada
        if not week_start_date:
            current_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
            days_since_monday = current_date.weekday()
            week_start = (current_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            week_start = week_start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end_date = week_start + timedelta(days=6)

        # 1. Obtener TODAS las disponibilidades activas del docente (por día de semana)
        availability_query = select(Availability).where(
            Availability.user_id == teacher_id,
            Availability.is_active == True
        ).order_by(Availability.day_of_week, Availability.start_time)
        
        availability_result = await db.execute(availability_query)
        all_availabilities = availability_result.scalars().all()
        
        # 2. Obtener TODAS las reservas del docente en el rango de fechas, filtrar por docente usando Availability
        booking_query = select(Booking).join(
            Availability, Booking.availability_id == Availability.id
        ).join(
            Status, Booking.status_id == Status.id
        ).options(selectinload(Booking.status)).where(
            Availability.user_id == teacher_id,
            Booking.start_time >= week_start,
            Booking.start_time <= week_end_date + timedelta(days=1),
            Status.name.in_(["active", "approved", "paid", "occupied"])
        ).order_by(Booking.start_time)
        
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()

        # 3. Construir la agenda (lógica por horas + overlay de reservas)
        days = []
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_date = week_start
        
        for i in range(7):
            python_weekday = current_date.weekday()
            our_day_of_week = python_weekday + 1

            day_availabilities = [
                av for av in all_availabilities 
                if av.day_of_week == our_day_of_week
            ]
            
            day_bookings = [
                booking for booking in bookings 
                if booking.start_time.date() == current_date.date()
            ]
            
            # Mapa de slots por hora: "HH:MM" -> slot
            slot_map: Dict[str, Dict] = {}

            # 1) Generar slots por hora desde disponibilidades activas (default: available)
            for av in day_availabilities:
                try:
                    av_start_dt = datetime.combine(current_date.date(), datetime.strptime(av.start_time, "%H:%M:%S").time())
                    av_end_dt = datetime.combine(current_date.date(), datetime.strptime(av.end_time, "%H:%M:%S").time())
                    if av_end_dt <= av_start_dt:
                        av_end_dt += timedelta(days=1)
                    cur = av_start_dt
                    while cur < av_end_dt:
                        nxt = cur + timedelta(hours=1)
                        key = cur.strftime("%H:%M")
                        slot_map[key] = {
                            "start_time": key,
                            "end_time": nxt.strftime("%H:%M"),
                            "status": "available",
                            "availability_id": av.id,
                        }
                        cur = nxt
                except Exception:
                    continue

            # 2) Superponer reservas: crear/actualizar slots como occupied aunque no exista disponibilidad
            for bk in day_bookings:
                # Alinear al inicio de la hora (asumimos reservas creadas en horas exactas)
                cur = bk.start_time.replace(minute=0, second=0, microsecond=0)
                end = bk.end_time
                while cur < end:
                    nxt = cur + timedelta(hours=1)
                    key = cur.strftime("%H:%M")
                    if key not in slot_map:
                        slot_map[key] = {
                            "start_time": key,
                            "end_time": nxt.strftime("%H:%M"),
                            "status": "occupied",
                            "availability_id": getattr(bk, "availability_id", None),
                        }
                    else:
                        slot_map[key]["status"] = "occupied"
                        if not slot_map[key].get("availability_id"):
                            slot_map[key]["availability_id"] = getattr(bk, "availability_id", None)
                    cur = nxt

            day_slots = sorted(slot_map.values(), key=lambda x: x["start_time"])
            
            days.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_name": day_names[python_weekday],
                "slots": day_slots
            })
            
            current_date += timedelta(days=1)
        
        teacher = await db.get(User, teacher_id)
        return {
            "teacher_id": teacher_id,
            "teacher_name": f"{teacher.first_name} {teacher.last_name}",
            "week_start": week_start.strftime('%Y-%m-%d'),
            "week_end": week_end_date.strftime('%Y-%m-%d'),
            "days": days
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error obteniendo agenda: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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
            Availability.start_time <= end_date,
            Availability.is_active == True
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
        
        # 1. Obtener TODAS las disponibilidades activas del docente
        availability_query = select(Availability).options(
            selectinload(Availability.preference)
        ).where(
            Availability.user_id == teacher_id,
            Availability.is_active == True
        ).order_by(Availability.day_of_week, Availability.start_time)
        
        availability_result = await db.execute(availability_query)
        all_availabilities = availability_result.scalars().all()
        
        # 2. Obtener reservas ocupadas del docente en el rango de fechas, filtrar por docente usando Availability
        booking_query = select(Booking).join(
            Availability, Booking.availability_id == Availability.id
        ).join(
            Status, Booking.status_id == Status.id
        ).options(selectinload(Booking.status)).where(
            Availability.user_id == teacher_id,
            Booking.start_time >= week_start,
            Booking.start_time <= week_end_date + timedelta(days=1),
            Status.name.in_(["active", "approved", "paid", "occupied"])
        ).order_by(Booking.start_time)
        
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()
        
        
        # 3. Construir la agenda (días del rango especificado) con slots por hora + overlay de reservas
        days = []
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_date = week_start
        
        for i in range(num_days):  # Iterar sobre el número de días del rango
            python_weekday = current_date.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
            our_day_of_week = python_weekday + 1 if python_weekday < 6 else 7  # 1=Monday, ..., 7=Sunday
                        
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
            
            # Mapa de slots por hora
            slot_map: Dict[str, Dict] = {}

            # 1) Generar slots por hora desde disponibilidades activas (default: available)
            for av in day_availabilities:
                try:
                    av_start_dt = datetime.combine(current_date.date(), datetime.strptime(av.start_time, "%H:%M:%S").time())
                    av_end_dt = datetime.combine(current_date.date(), datetime.strptime(av.end_time, "%H:%M:%S").time())
                    if av_end_dt <= av_start_dt:
                        av_end_dt += timedelta(days=1)
                    cur = av_start_dt
                    while cur < av_end_dt:
                        nxt = cur + timedelta(hours=1)
                        key = cur.strftime("%H:%M")
                        slot_map[key] = {
                            "start_time": key,
                            "end_time": nxt.strftime("%H:%M"),
                            "status": "available",
                            "availability_id": av.id,
                        }
                        cur = nxt
                except Exception:
                    continue

            # 2) Superponer reservas: crear/actualizar slots como occupied aunque no exista disponibilidad
            for bk in day_bookings:
                cur = bk.start_time.replace(minute=0, second=0, microsecond=0)
                end = bk.end_time
                while cur < end:
                    nxt = cur + timedelta(hours=1)
                    key = cur.strftime("%H:%M")
                    if key not in slot_map:
                        slot_map[key] = {
                            "start_time": key,
                            "end_time": nxt.strftime("%H:%M"),
                            "status": "occupied",
                            "availability_id": getattr(bk, "availability_id", None),
                        }
                    else:
                        slot_map[key]["status"] = "occupied"
                        if not slot_map[key].get("availability_id"):
                            slot_map[key]["availability_id"] = getattr(bk, "availability_id", None)
                    cur = nxt

            day_slots = sorted(slot_map.values(), key=lambda x: x["start_time"])
            
            days.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_name": day_names[python_weekday],
                "slots": day_slots,
                "total_slots": len(day_slots),
                "available_slots": len([s for s in day_slots if s["status"] == "available"]),
                "occupied_slots": len([s for s in day_slots if s["status"] == "occupied"]),
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
                "occupied_slots": sum(d["occupied_slots"] for d in days),
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
) -> Availability:
    """
    Actualizar una disponibilidad existente del docente.
    """
    try:
        teacher_id = user_data["user_id"]
        
        availability_query = select(Availability).where(
            Availability.id == availability_id,
            Availability.user_id == teacher_id
        )
        availability_result = await db.execute(availability_query)
        availability = availability_result.scalar_one_or_none()
        
        if not availability:
            raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

        # Validar y actualizar campos si se proporcionan
        if "start_time" in availability_data and "end_time" in availability_data:
            from datetime import time as dt_time
            start_time = dt_time.fromisoformat(availability_data["start_time"])
            end_time = dt_time.fromisoformat(availability_data["end_time"])
            
            if start_time >= end_time:
                await db.rollback()
                raise HTTPException(status_code=400, detail="La hora de inicio debe ser anterior a la hora de fin")

            availability.start_time = availability_data["start_time"]
            availability.end_time = availability_data["end_time"]

        if "day_of_week" in availability_data:
            availability.day_of_week = availability_data["day_of_week"]

        if "is_active" in availability_data:
            availability.is_active = availability_data["is_active"]

        await db.commit()
        await db.refresh(availability)
        return availability

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error actualizando disponibilidad: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def delete_teacher_availability(
    db: AsyncSession,
    user_data: dict,
    availability_id: int
) -> Dict:
    """
    Elimina una disponibilidad de forma inteligente:
    - Si hay reservas (pasadas o futuras), la desactiva (soft delete).
    - Si no hay ninguna reserva asociada, la elimina permanentemente (hard delete).
    """
    try:
        teacher_id = user_data["user_id"]
        
        availability = await db.get(Availability, availability_id)
        if not availability or availability.user_id != teacher_id:
            raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

        # 1. Contar TODAS las reservas asociadas a esta disponibilidad
        total_bookings_query = select(func.count(Booking.id)).where(
            Booking.availability_id == availability_id
        )
        total_bookings_count = await db.scalar(total_bookings_query)

        # 2. Si hay CUALQUIER reserva (pasada o futura), se desactiva
        if total_bookings_count > 0:
            availability.is_active = False
            await db.commit()
            
            # (Opcional) Verificar si alguna de esas reservas es futura para dar una advertencia más específica
            future_bookings_query = select(func.count(Booking.id)).where(
                Booking.availability_id == availability_id,
                Booking.start_time >= datetime.now()
            )
            future_bookings_count = await db.scalar(future_bookings_query)

            # Mensaje claro para el usuario (singular/plural y acciones)
            if future_bookings_count and future_bookings_count > 0:
                palabra = "reserva" if future_bookings_count == 1 else "reservas"
                adjetivo = "futura" if future_bookings_count == 1 else "futuras"
                message = (
                    f"La disponibilidad fue eliminada del listado y desactivada para nuevas reservas, "
                    f"pero tienes {future_bookings_count} {palabra} {adjetivo} que debes cumplir. "
                    f"Las clases ya agendadas se mantienen."
                )
            else:
                message = (
                    "La disponibilidad fue eliminada del listado y desactivada para mantener el historial de reservas. "
                    "No se permite la eliminación definitiva mientras existan reservas asociadas."
                )

            return {"warning": message, "action": "deactivated"}
        else:
            # 3. Si no hay NINGUNA reserva, se elimina permanentemente
            await db.delete(availability)
            await db.commit()
            return {"warning": None, "action": "deleted"}
        
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
        
        # Obtener todas las disponibilidades activas del docente
        query = select(Availability).where(
            Availability.user_id == teacher_id,
            Availability.is_active == True
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

def generate_time_slots(availability: Availability, bookings: List[Booking]) -> List[Dict]:
    """
    Generar slots de tiempo por horas exactas para una disponibilidad
    """
    slots = []
    current_time = datetime.strptime(availability.start_time, "%H:%M:%S")  # Ya es datetime
    end_time = datetime.strptime(availability.end_time, "%H:%M:%S")  # Ya es datetime
    
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
