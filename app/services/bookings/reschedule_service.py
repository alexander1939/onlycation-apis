from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
from fastapi import HTTPException

from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.booking.confirmation import Confirmation
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.reschedule_request import RescheduleRequest
from app.services.notifications.booking_notification_service import send_booking_rescheduled_notification
from app.services.notifications.booking_email_service import send_booking_rescheduled_email

logger = logging.getLogger(__name__)

async def reschedule_booking(
    db: AsyncSession,
    student_id: int,
    booking_id: int,
    new_availability_id: Optional[int] = None,
    new_start_time: Optional[datetime] = None,
    new_end_time: Optional[datetime] = None,
    items: Optional[List[Dict]] = None,
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
        
        # Validar que la reserva no esté cancelada
        from app.models.common.status import Status
        cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
        cancelled_status = cancelled_status_result.scalar_one_or_none()
        
        if cancelled_status and booking.status_id == cancelled_status.id:
            raise HTTPException(status_code=400, detail="No puedes reagendar una reserva que ya está cancelada")
        
        # Fallback adicional: si el booking ya fue actualizado (updated_at > created_at),
        # asumir que ya hubo un reagendo previo y bloquear.
        try:
            if booking.updated_at and booking.created_at:
                # Normalizar a naive para comparación segura
                b_upd = booking.updated_at.replace(tzinfo=None) if getattr(booking.updated_at, "tzinfo", None) else booking.updated_at
                b_cre = booking.created_at.replace(tzinfo=None) if getattr(booking.created_at, "tzinfo", None) else booking.created_at
                if (b_upd - b_cre).total_seconds() > 1:
                    raise HTTPException(status_code=400, detail="Solo puedes reagendar esta clase una vez")
        except Exception:
            # Si hay cualquier problema con los timestamps, no interrumpir el flujo por aquí
            pass
        
        # VALIDAR: Solo se permite reagendar una vez por alumno para esta reserva
        existing_rr_q = select(RescheduleRequest).where(
            RescheduleRequest.booking_id == booking_id,
            RescheduleRequest.student_id == student_id,
            RescheduleRequest.status == "completed",
            RescheduleRequest.reason == "student_direct_reschedule",
        )
        existing_rr = (await db.execute(existing_rr_q)).scalars().first()
        if existing_rr:
            raise HTTPException(status_code=400, detail="Solo puedes reagendar esta clase una vez")
        
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
        
        # Soportar modo 'items' (varias horas por hora) o modo simple
        teacher_id_ref = booking.availability.user_id
        if items:
            if not isinstance(items, list) or len(items) == 0:
                raise HTTPException(status_code=400, detail="Debes enviar al menos un tramo en 'items' para reagendar")
            
            # Helper para leer atributos tanto de dict como de objeto Pydantic
            def get_field(obj, name):
                if hasattr(obj, name):
                    return getattr(obj, name)
                if isinstance(obj, dict):
                    return obj.get(name)
                return None
            
            # Helper para parsear ISO8601 (acepta 'Z') y normalizar a naive
            def parse_to_naive(val):
                from datetime import datetime as _dt
                if isinstance(val, _dt):
                    dt = val
                elif isinstance(val, str):
                    s = val.replace("Z", "+00:00")
                    try:
                        dt = _dt.fromisoformat(s)
                    except Exception:
                        raise HTTPException(status_code=400, detail="Formato de fecha inválido en items (use ISO 8601)")
                else:
                    raise HTTPException(status_code=400, detail="Formato de fecha inválido en items")
                # Normalizar a naive (coherente con lógica previa del servicio)
                if getattr(dt, "tzinfo", None) is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            
            # Helper para parsear hora de Availability (string HH:MM o HH:MM:SS) a objeto time
            def parse_av_time_str(s: str):
                from datetime import datetime as _dt
                if not isinstance(s, str):
                    raise HTTPException(status_code=500, detail="Formato de disponibilidad inválido (hora)")
                for fmt in ("%H:%M:%S", "%H:%M"):
                    try:
                        return _dt.strptime(s, fmt).time()
                    except Exception:
                        continue
                raise HTTPException(status_code=500, detail="Formato de hora de disponibilidad inválido (use HH:MM[:SS])")
            
            # Cargar todas las disponibilidades referenciadas en items
            ids = set()
            for it in items:
                aid = get_field(it, "availability_id")
                if aid is None:
                    raise HTTPException(status_code=400, detail="Cada tramo debe incluir availability_id")
                ids.add(int(aid))
            res_av = await db.execute(select(Availability).where(Availability.id.in_(ids)))
            av_list = res_av.scalars().all()
            av_map = {a.id: a for a in av_list}
            if len(av_map) != len(ids):
                raise HTTPException(status_code=404, detail="Alguna disponibilidad indicada no existe")
            
            # Validar que todas pertenezcan al mismo docente
            for a in av_list:
                if a.user_id != teacher_id_ref:
                    raise HTTPException(status_code=400, detail="Todas las disponibilidades deben pertenecer al mismo docente de la reserva")
            
            # Normalizar y ordenar tramos por start_time
            norm_items = []
            for it in items:
                aid = int(get_field(it, "availability_id"))
                st = parse_to_naive(get_field(it, "start_time"))
                et = parse_to_naive(get_field(it, "end_time"))
                # HH:00 exacto por tramo
                if st.minute != 0 or st.second != 0 or et.minute != 0 or et.second != 0:
                    raise HTTPException(status_code=400, detail="Todos los tramos deben iniciar y terminar en hora exacta (HH:00)")
                if et <= st:
                    raise HTTPException(status_code=400, detail="Cada tramo debe tener fin mayor al inicio")
                av = av_map[aid]
                # Availability guarda horas como string -> comparar por time-of-day
                av_start_t = parse_av_time_str(av.start_time)
                av_end_t = parse_av_time_str(av.end_time)
                if not (av_start_t <= st.time() and et.time() <= av_end_t):
                    raise HTTPException(status_code=400, detail="Algún tramo no está dentro de la disponibilidad indicada")
                norm_items.append({"availability_id": aid, "start_time": st, "end_time": et})
            
            norm_items.sort(key=lambda x: x["start_time"])
            first_start = norm_items[0]["start_time"]
            last_end = norm_items[-1]["end_time"]
            
            # Tramos contiguos sin huecos
            for i in range(1, len(norm_items)):
                if norm_items[i]["start_time"] != norm_items[i-1]["end_time"]:
                    raise HTTPException(status_code=400, detail="Los tramos deben ser contiguos (sin huecos)")
            
            # No se puede reagendar al pasado
            if first_start <= current_time:
                raise HTTPException(status_code=400, detail="No puedes reagendar a una hora que ya pasó. El nuevo horario debe ser en el futuro.")
            
            # Debe reagendarse para después del fin de la reserva actual
            if first_start < booking.end_time:
                raise HTTPException(status_code=400, detail=f"Solo puedes reagendar para después de tu reserva actual. Tu clase termina a las {booking.end_time.strftime('%H:%M')} del {booking.end_time.strftime('%d/%m/%Y')}.")
            
            # Duración debe coincidir con la original
            original_secs = (booking.end_time - booking.start_time).total_seconds()
            new_secs = (last_end - first_start).total_seconds()
            if int(new_secs) != int(original_secs):
                raise HTTPException(status_code=400, detail="La nueva duración debe coincidir con la duración original de la reserva")
            
            # Verificar conflictos a nivel docente (cualquier availability del mismo docente)
            from app.models.common.status import Status
            cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
            cancelled_status = cancelled_status_result.scalar_one_or_none()
            cancelled_status_id = cancelled_status.id if cancelled_status else None
            
            conflict_query = select(Booking).join(Availability, Booking.availability_id == Availability.id).where(
                Availability.user_id == teacher_id_ref,
                Booking.id != booking_id,
                Booking.start_time < last_end,
                Booking.end_time > first_start,
                Booking.status_id != cancelled_status_id if cancelled_status_id else True
            )
            conflict_result = await db.execute(conflict_query)
            conflicting_booking = conflict_result.scalar_one_or_none()
            if conflicting_booking:
                raise HTTPException(status_code=409, detail="Ya existe una reserva en el nuevo horario solicitado")
            
            # Datos para actualizar
            selected_availability_id = norm_items[0]["availability_id"]
            new_av_start = first_start
            new_av_end = last_end
        else:
            # Modo simple original
            # Verificar que la nueva disponibilidad existe y pertenece al mismo docente
            new_availability_query = select(Availability).where(
                Availability.id == new_availability_id,
                Availability.user_id == teacher_id_ref  # Mismo docente
            )
            new_availability_result = await db.execute(new_availability_query)
            new_availability = new_availability_result.scalar_one_or_none()
            if not new_availability:
                raise HTTPException(status_code=404, detail="La nueva disponibilidad no existe o no pertenece al mismo docente")
            
            # Parsear y normalizar a naive entradas del modo simple (por si llegan como string ISO o aware)
            def _parse_simple_dt(val):
                from datetime import datetime as _dt
                if isinstance(val, _dt):
                    dt = val
                elif isinstance(val, str):
                    s = val.replace("Z", "+00:00")
                    try:
                        dt = _dt.fromisoformat(s)
                    except Exception:
                        raise HTTPException(status_code=400, detail="Formato de fecha inválido (use ISO 8601)")
                else:
                    raise HTTPException(status_code=400, detail="Formato de fecha inválido en fechas de reagendo")
                # Normalizar a naive (coherente con lógica previa del servicio)
                if getattr(dt, "tzinfo", None) is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            
            new_start_time = _parse_simple_dt(new_start_time)
            new_end_time = _parse_simple_dt(new_end_time)
            
            # Availability guarda horas como string -> comparar por time-of-day
            av_start_t = parse_av_time_str(new_availability.start_time)
            av_end_t = parse_av_time_str(new_availability.end_time)
            
            # Validar rango dentro de disponibilidad
            if not (av_start_t <= new_start_time.time() and new_end_time.time() <= av_end_t):
                raise HTTPException(status_code=400, detail="El nuevo horario no está dentro de la disponibilidad del docente")
            
            # HH:00 exacto
            if new_start_time.minute != 0 or new_start_time.second != 0:
                raise HTTPException(status_code=400, detail="El horario de inicio debe ser en hora exacta (ej: 9:00, 10:00, no 9:30)")
            if new_end_time.minute != 0 or new_end_time.second != 0:
                raise HTTPException(status_code=400, detail="El horario de fin debe ser en hora exacta (ej: 10:00, 11:00, no 10:30)")
            if new_end_time <= new_start_time:
                raise HTTPException(status_code=400, detail="La hora de fin debe ser después de la hora de inicio")
            if new_start_time <= current_time:
                raise HTTPException(status_code=400, detail="No puedes reagendar a una hora que ya pasó. El nuevo horario debe ser en el futuro.")
            
            # Normalizar fin actual de booking a naive para comparar
            bk_end = booking.end_time
            if getattr(bk_end, "tzinfo", None) is not None:
                bk_end = bk_end.replace(tzinfo=None)
            if new_start_time < bk_end:
                raise HTTPException(status_code=400, detail=f"Solo puedes reagendar para después de tu reserva actual. Tu clase termina a las {booking.end_time.strftime('%H:%M')} del {booking.end_time.strftime('%d/%m/%Y')}.")
            
            # Verificar conflictos solo en esa availability
            from app.models.common.status import Status
            cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
            cancelled_status = cancelled_status_result.scalar_one_or_none()
            cancelled_status_id = cancelled_status.id if cancelled_status else None
            conflict_query = select(Booking).where(
                Booking.availability_id == new_availability_id,
                Booking.id != booking_id,
                Booking.start_time < new_end_time,
                Booking.end_time > new_start_time,
                Booking.status_id != cancelled_status_id if cancelled_status_id else True
            )
            conflict_result = await db.execute(conflict_query)
            conflicting_booking = conflict_result.scalar_one_or_none()
            if conflicting_booking:
                raise HTTPException(status_code=409, detail="Ya existe una reserva en el nuevo horario solicitado")
            
            selected_availability_id = new_availability_id
            new_av_start = new_start_time
            new_av_end = new_end_time
        
        teacher_id = booking.availability.user_id
        teacher_name = f"{booking.availability.user.first_name} {booking.availability.user.last_name}"
        old_availability_id = booking.availability_id
        old_start_time = booking.start_time
        old_end_time = booking.end_time
        
        # Actualizar la reserva
        booking.availability_id = selected_availability_id
        booking.start_time = new_av_start
        booking.end_time = new_av_end
        booking.updated_at = datetime.utcnow()
        
        # Registrar evento de reagendado directo por alumno (para limitar a 1)
        rr = RescheduleRequest(
            booking_id=booking.id,
            teacher_id=teacher_id,
            student_id=student_id,
            current_availability_id=old_availability_id,
            current_start_time=old_start_time,
            current_end_time=old_end_time,
            new_availability_id=selected_availability_id,
            new_start_time=new_av_start,
            new_end_time=new_av_end,
            reason="student_direct_reschedule",
            status="completed",
            responded_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        )
        db.add(rr)
        
        await db.commit()
        await db.refresh(booking)
        
        logger.info(f"✅ Reserva {booking_id} reagendada exitosamente para el estudiante {student_id}")
        
        # Enviar notificaciones de reagendado a ambos usuarios
        notification_details = {}
        await send_booking_rescheduled_notification(db, student_id, notification_details)
        await send_booking_rescheduled_notification(db, teacher_id, notification_details)
        
        # Enviar emails con información detallada
        email_details = {
            'booking_id': booking.id,
            'old_start_date': old_start_time.strftime('%d/%m/%Y %H:%M'),
            'old_end_date': old_end_time.strftime('%d/%m/%Y %H:%M'),
            'new_start_date': new_av_start.strftime('%d/%m/%Y %H:%M'),
            'new_end_date': new_av_end.strftime('%d/%m/%Y %H:%M')
        }
        await send_booking_rescheduled_email(db, student_id, email_details)
        await send_booking_rescheduled_email(db, teacher_id, email_details)
        
        return {
            "booking_id": booking.id,
            "old_start_time": old_start_time.isoformat(),
            "old_end_time": old_end_time.isoformat(),
            "new_start_time": new_av_start.isoformat(),
            "new_end_time": new_av_end.isoformat(),
            "teacher_name": teacher_name,
            "updated_at": booking.updated_at.isoformat(),
            # Política: solo un reagendo directo por alumno → después de este reagendo ya no puede volver a hacerlo
            "can_reschedule_again": False,
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
