from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
import json

# Helpers de normalización a hora local (MX, UTC-06) como datetime naive
def _to_mx_local_naive(d: datetime | str) -> datetime:
    """
    Convierte un datetime o string ISO (con o sin 'Z') a hora local de MX (UTC-06) sin tz.
    - Si el datetime es tz-aware, se convierte desde su tz a UTC y luego se resta 6h para obtener hora local.
    - Si es naive, se asume ya en hora local MX y se deja igual.
    """
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d.replace("Z", "+00:00"))
        except Exception:
            d = datetime.fromisoformat(d)
    if getattr(d, "tzinfo", None) is not None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
    return d

def _now_mx_local() -> datetime:
    """Devuelve 'ahora' en hora local de MX (UTC-06) como datetime naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)

from app.models.teachers.availability import Availability
from app.models.teachers.price import Price
from app.models.users.user import User
from app.external.stripe_config import stripe
from app.services.bookings.commission_service import get_teacher_commission_rate, get_teacher_wallet, calculate_commission_amounts

async def create_booking_payment_session(db: AsyncSession, user: User, booking_data):
    # 1. Validar que la disponibilidad existe y cargar la relación user
    disponibilidad_result = await db.execute(
        select(Availability)
        .options(joinedload(Availability.user))
        .where(Availability.id == booking_data.availability_id)
    )
    disponibilidad = disponibilidad_result.scalar_one_or_none()

    if not disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    # Modo MULTI-SEGMENTOS: si el request trae 'items', procesar varios tramos en una sola sesión
    if getattr(booking_data, "items", None):
        # 2. Cargar disponibilidades de todos los segmentos y validar mismo docente y preference
        segment_ids = list({int(i.availability_id) for i in booking_data.items})
        seg_avails_result = await db.execute(
            select(Availability)
            .options(joinedload(Availability.user))
            .where(Availability.id.in_(segment_ids))
        )
        seg_avails = {a.id: a for a in seg_avails_result.scalars().all()}
        if len(seg_avails) != len(segment_ids):
            raise HTTPException(status_code=404, detail="Alguna disponibilidad indicada en 'items' no existe")

        base_avail = seg_avails[segment_ids[0]]
        teacher_id = base_avail.user_id
        preference_id = base_avail.preference_id
        for aid in segment_ids:
            av = seg_avails[aid]
            if av.user_id != teacher_id or av.preference_id != preference_id:
                raise HTTPException(status_code=400, detail="Todas las horas deben ser del mismo docente y misma materia/nivel")

        # 3. Parsear y validar segmentos (HH:00, día correcto)
        segments = []
        for it in booking_data.items:
            s = _to_mx_local_naive(it.start_time)
            e = _to_mx_local_naive(it.end_time)
            if (s.minute or s.second or s.microsecond or e.minute or e.second or e.microsecond):
                raise HTTPException(status_code=400, detail="Los horarios deben ser en horas exactas (ej: 09:00, 10:00)")
            if e <= s:
                raise HTTPException(status_code=400, detail="Las horas deben ser positivas y con fin > inicio")
            segments.append({"availability_id": int(it.availability_id), "start": s, "end": e})

        # Validar día correspondiente por segmento y recolectar días distintos
        distinct_weekdays = set()
        for seg in segments:
            seg_weekday = seg["start"].weekday() + 1
            # Cada segmento debe mantenerse en el mismo día calendario
            if (seg["end"].weekday() + 1) != seg_weekday:
                raise HTTPException(status_code=400, detail="Cada segmento debe estar dentro del mismo día")
            if seg_avails[seg["availability_id"]].day_of_week != seg_weekday:
                raise HTTPException(status_code=400, detail="La fecha seleccionada no corresponde al día de la disponibilidad")
            distinct_weekdays.add(seg_weekday)

        # 4. Validar que cada hora de cada segmento exista como availability activa
        avail_rows_result = await db.execute(
            select(Availability).where(
                Availability.user_id == teacher_id,
                Availability.preference_id == preference_id,
                Availability.day_of_week.in_(distinct_weekdays),
                Availability.is_active == True,
            )
        )
        avail_rows = avail_rows_result.scalars().all()
        day_avail_map = {}
        for r in avail_rows:
            day_avail_map.setdefault(r.day_of_week, set()).add((r.start_time, r.end_time))
        missing = []
        for seg in segments:
            cur = seg["start"]
            seg_weekday = cur.weekday() + 1
            day_set = day_avail_map.get(seg_weekday, set())
            while cur < seg["end"]:
                nxt = cur + timedelta(hours=1)
                if (f"{cur.hour:02d}:00:00", f"{nxt.hour:02d}:00:00") not in day_set:
                    missing.append(f"{cur.strftime('%Y-%m-%d')} {cur.hour:02d}:00-{nxt.hour:02d}:00")
                cur = nxt
        if missing:
            raise HTTPException(status_code=400, detail=f"Las horas seleccionadas no están disponibles: {', '.join(missing)}")

        # 5. Validar traslapes con otras reservas del docente y del alumno
        from app.models.booking.bookings import Booking
        from app.models.common.status import Status
        cancelled_status = (await db.execute(select(Status).where(Status.name == "cancelled"))).scalar_one_or_none()
        cancelled_id = cancelled_status.id if cancelled_status else None
        for seg in segments:
            r_teacher = await db.execute(
                select(Booking)
                .join(Availability, Booking.availability_id == Availability.id)
                .where(
                    Availability.user_id == teacher_id,
                    Booking.start_time < seg["end"],
                    Booking.end_time > seg["start"],
                    Booking.status_id != cancelled_id if cancelled_id else True,
                )
            )
            if r_teacher.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Ya existe una reserva en alguno de los tramos seleccionados")
            r_user = await db.execute(
                select(Booking).where(
                    Booking.user_id == user.id,
                    Booking.start_time < seg["end"],
                    Booking.end_time > seg["start"],
                    Booking.status_id != cancelled_id if cancelled_id else True,
                )
            )
            if r_user.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Ya tienes una reserva que traslapa con alguno de los tramos seleccionados")

        # 6. Anticipación mínima sobre el primer inicio
        min_start = min(s["start"] for s in segments)
        if ((min_start - _now_mx_local()).total_seconds() / 3600) < 1:
            raise HTTPException(status_code=400, detail="Debes reservar la clase con al menos 1 hora de anticipación")

        # 7. Obtener precio y wallet/commissions
        price = (await db.execute(select(Price).where(Price.user_id == teacher_id, Price.preference_id == preference_id))).scalar_one_or_none()
        if not price:
            raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")
        commission_rate = await get_teacher_commission_rate(db, teacher_id)
        teacher_wallet = await get_teacher_wallet(db, teacher_id)

        # 8. Agrupar segmentos en Asesoriass contiguos (hora extra solo dentro del Asesorias)
        segments.sort(key=lambda x: x["start"])
        blocks = []
        b_s, b_e = segments[0]["start"], segments[0]["end"]
        for seg in segments[1:]:
            if seg["start"] == b_e:
                b_e = seg["end"]
            else:
                blocks.append({"start": b_s, "end": b_e})
                b_s, b_e = seg["start"], seg["end"]
        blocks.append({"start": b_s, "end": b_e})

        # 9. Calcular precios por Asesorias y construir line_items
        line_items = []
        blocks_meta = []
        total_amount_cents = 0
        total_hours_all = 0
        total_commission_amount = 0
        total_teacher_amount = 0
        # Política por bloque: primeras 2 horas de CADA Asesoría a precio base; desde la 3ra hora del bloque, precio extra
        base_cents = int(float(price.selected_prices) * 100)
        extra_cents = int(float(price.extra_hour_price) * 100)
        for idx, blk in enumerate(blocks, 1):
            hours = int((blk["end"] - blk["start"]).total_seconds() // 3600)
            if hours <= 0:
                raise HTTPException(status_code=400, detail="Cada Asesorias debe tener duración positiva en horas")
            # Calcular monto del bloque: 2 primeras horas base, resto extra (por bloque)
            block_amount_cents = base_cents * min(hours, 2) + extra_cents * max(0, hours - 2)
            c_amt, t_amt = calculate_commission_amounts(block_amount_cents, commission_rate)
            total_commission_amount += c_amt
            total_teacher_amount += t_amt
            total_amount_cents += block_amount_cents
            total_hours_all += hours

            # availability_id del Asesorias: el del primer segmento que inicia el Asesorias
            try:
                availability_id_for_block = next(seg["availability_id"] for seg in segments if seg["start"] == blk["start"])  # type: ignore
            except StopIteration:
                availability_id_for_block = segments[0]["availability_id"] if segments else base_avail.id  # fallback

            line_items.append({
                "price_data": {
                    "currency": "mxn",
                    "product_data": {
                        "name": f"Clase con {base_avail.user.first_name} {base_avail.user.last_name} - Asesoria {idx}",
                        "description": f"Asesoria de {hours}h - {blk['start'].strftime('%d/%m/%Y %H:%M')} a {blk['end'].strftime('%d/%m/%Y %H:%M')}",
                    },
                    "unit_amount": block_amount_cents,
                },
                "quantity": 1,
            })
            # Usar claves cortas para mantener metadata < 500 chars por valor
            blocks_meta.append({
                "s": blk["start"].isoformat(),
                "e": blk["end"].isoformat(),
                "h": hours,
                "a": int(availability_id_for_block),
                "p": block_amount_cents,
            })

        # 10. Crear sesión Stripe con múltiples line_items
        session_data = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": "payment",
            "success_url": "https://onlycation.com/catalog/teachers/?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://onlycation.com",
            "customer_email": user.email,
            "metadata": {
                "booking_mode": "multi",
                "user_id": str(user.id),
                "price_id": str(price.id),
                "availability_id": str(booking_data.availability_id),  # compat
                "teacher_id": str(teacher_id),
                "teacher_email": base_avail.user.email,
                "commission_rate": str(commission_rate),
                "commission_amount": str(total_commission_amount),
                "teacher_amount": str(total_teacher_amount),
                "teacher_stripe_account_id": teacher_wallet.stripe_account_id,
                "total_hours": str(total_hours_all),
                # Solo enviamos Asesoriass con claves cortas para no exceder el límite de 500 chars por valor
                "blocks": json.dumps(blocks_meta, separators=(",", ":")),
                "global_pricing_policy": "Por asesoría. Las primeras 2 horas a precio normal; desde la 3ra hora de la misma asesoría, el costo es a mitad de precio.",
            },
        }
        if total_commission_amount > 0:
            session_data["payment_intent_data"] = {
                "application_fee_amount": total_commission_amount,
                "transfer_data": {"destination": teacher_wallet.stripe_account_id},
            }
        else:
            session_data["payment_intent_data"] = {
                "transfer_data": {"destination": teacher_wallet.stripe_account_id},
            }

        session = stripe.checkout.Session.create(**session_data)
        return {"url": session.url, "session_id": session.id, "price": total_amount_cents / 100.0}

    # 2. Convertir fechas para validaciones
    requested_start = _to_mx_local_naive(booking_data.start_time)
    requested_end = _to_mx_local_naive(booking_data.end_time)
        
    # 2.b Validar que los horarios sean en horas exactas (HH:00) para garantizar Asesoriass corridos
    if (
        requested_start.minute != 0 or requested_start.second != 0 or requested_start.microsecond != 0 or
        requested_end.minute != 0 or requested_end.second != 0 or requested_end.microsecond != 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Los horarios deben ser en horas exactas (ej: 09:00, 10:00)"
        )

    # 3. Validar que no se puede reservar en fechas pasadas
    current_time = _now_mx_local()
    if requested_start <= current_time:
        raise HTTPException(
            status_code=400,
            detail="No se puede reservar una clase en una fecha y hora que ya pasó"
        )
    
    if requested_end <= current_time:
        raise HTTPException(
            status_code=400,
            detail="La hora de fin de la clase no puede ser en el pasado"
        )

    # 4. Validar que el día y rango solicitado están dentro de la disponibilidad del docente
    #    Availability guarda horas como strings HH:MM:SS y un day_of_week (1=Lunes..7=Domingo)
    python_weekday = requested_start.weekday()  # 0=Lunes
    if (python_weekday + 1) != disponibilidad.day_of_week:
        raise HTTPException(
            status_code=400,
            detail="La fecha seleccionada no corresponde al día de la disponibilidad"
        )

    # 4.b La reserva debe estar dentro del mismo día calendario
    if requested_start.date() != requested_end.date():
        raise HTTPException(status_code=400, detail="La reserva debe estar dentro del mismo día")

    # 4.c Validar que CADA hora solicitada exista como Availability (per-hour) para el mismo docente/preferencia
    avail_rows_result = await db.execute(
        select(Availability).where(
            Availability.user_id == disponibilidad.user_id,
            Availability.preference_id == disponibilidad.preference_id,
            Availability.day_of_week == (python_weekday + 1),
            Availability.is_active == True,
        )
    )
    avail_rows = avail_rows_result.scalars().all()
    avail_set = {(row.start_time, row.end_time) for row in avail_rows}

    # Generar los Asesoriass horarios requeridos [start, end) en pasos de 1h
    check_cursor = requested_start
    missing_hours = []
    while check_cursor < requested_end:
        slot_start_str = f"{check_cursor.hour:02d}:00:00"
        slot_end = check_cursor + timedelta(hours=1)
        slot_end_str = f"{slot_end.hour:02d}:00:00"
        if (slot_start_str, slot_end_str) not in avail_set:
            missing_hours.append(f"{slot_start_str[:-3]}-{slot_end_str[:-3]}")
        check_cursor = slot_end

    if missing_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Las horas seleccionadas no están disponibles: {', '.join(missing_hours)}"
        )

    # 5. Validar que no hay traslape con otra reserva ya existente en esa disponibilidad
    from app.models.booking.bookings import Booking
    from app.models.common.status import Status
    
    # Obtener el ID del status 'cancelled'
    cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
    cancelled_status = cancelled_status_result.scalar_one_or_none()
    cancelled_status_id = cancelled_status.id if cancelled_status else None
    
    # Buscar traslapes en CUALQUIER reserva del mismo docente en esa ventana
    overlap_result = await db.execute(
        select(Booking)
        .join(Availability, Booking.availability_id == Availability.id)
        .where(
            Availability.user_id == disponibilidad.user_id,
            Booking.start_time < requested_end,
            Booking.end_time > requested_start,
            Booking.status_id != cancelled_status_id if cancelled_status_id else True,
        )
    )
    existing_booking = overlap_result.scalar_one_or_none()
    if existing_booking:
        # Formatear las fechas para mostrar en el error
        existing_start = existing_booking.start_time.strftime('%d/%m/%Y %H:%M')
        existing_end = existing_booking.end_time.strftime('%d/%m/%Y %H:%M')
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una reserva en ese horario: {existing_start} - {existing_end}. Por favor selecciona otro horario."
        )

    # 6. Validar que el MISMO USUARIO no tenga otra reserva al mismo tiempo
    user_overlap_result = await db.execute(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.start_time < requested_end,
            Booking.end_time > requested_start,
            Booking.status_id != cancelled_status_id if cancelled_status_id else True
        )
    )
    user_existing_booking = user_overlap_result.scalar_one_or_none()
    if user_existing_booking:
        # Formatear las fechas para mostrar en el error
        user_existing_start = user_existing_booking.start_time.strftime('%d/%m/%Y %H:%M')
        user_existing_end = user_existing_booking.end_time.strftime('%d/%m/%Y %H:%M')
        raise HTTPException(
            status_code=400,
            detail=f"Ya tienes una reserva en ese horario: {user_existing_start} - {user_existing_end}. No puedes reservar dos clases al mismo tiempo."
        )

    # 7. Validar que la reserva tiene al menos 1 hora de anticipación
    time_difference = (requested_start - current_time).total_seconds() / 3600  # en horas, en MX local
    if time_difference < 1:
        raise HTTPException(
            status_code=400,
            detail="Debes reservar la clase con al menos 1 hora de anticipación"
        )

    # 8. Obtener el precio asociado al docente y preferencia
    price_result = await db.execute(
        select(Price).where(
            Price.user_id == disponibilidad.user_id,
            Price.preference_id == disponibilidad.preference_id
        )
    )
    price = price_result.scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")

    # 6. Obtener información del docente para comisiones
    teacher_id = disponibilidad.user_id
    
    commission_rate = await get_teacher_commission_rate(db, teacher_id)
    
    teacher_wallet = await get_teacher_wallet(db, teacher_id)

    # 7. Calcular el precio total basado en las horas
    total_hours = (requested_end - requested_start).total_seconds() / 3600

    if total_hours <= 0:
        raise HTTPException(status_code=400, detail="Las horas deben ser positivas")

    # Asegurar múltiplos de 1 hora exacta (Asesoriass corridos)
    if ((requested_end - requested_start).total_seconds() % 3600) != 0:
        raise HTTPException(status_code=400, detail="La duración debe ser en múltiplos de 1 hora (Asesoriass corridos)")

    # Calcular precio global (single): primeras 2 horas base, desde 3ra hora extra
    hours_n = int(total_hours)
    base_cents = int(float(price.selected_prices) * 100)
    extra_cents = int(float(price.extra_hour_price) * 100)
    total_amount_cents = base_cents * min(hours_n, 2) + extra_cents * max(0, hours_n - 2)
    
    # Calcular comisiones
    commission_amount, teacher_amount = calculate_commission_amounts(total_amount_cents, commission_rate)
    
    # 8. Crear sesión de pago en Stripe con Stripe Connect
    session_data = {
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price_data": {
                    "currency": "mxn",
                    "product_data": {
                        "name": f"Clase con {disponibilidad.user.first_name} {disponibilidad.user.last_name}",
                        "description": f"Clase de {int(total_hours)} hora(s) - {requested_start.strftime('%d/%m/%Y %H:%M')} a {requested_end.strftime('%d/%m/%Y %H:%M')}",
                    },
                    "unit_amount": total_amount_cents,
                },
                "quantity": 1,
            }
        ],
        "mode": "payment",
        "success_url": "https://onlycation.com/catalog/teachers/?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://onlycation.com/",
        "customer_email": user.email,  # Email del estudiante pre-llenado automáticamente
        "metadata": {
            "user_id": str(user.id),
            "price_id": str(price.id),
            "availability_id": str(booking_data.availability_id),
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "total_hours": str(total_hours),
            "teacher_id": str(teacher_id),
            "teacher_email": disponibilidad.user.email,  # Email del docente
            "commission_rate": str(commission_rate),
            "commission_amount": str(commission_amount),
            "teacher_amount": str(teacher_amount),
            "teacher_stripe_account_id": teacher_wallet.stripe_account_id,
            "global_pricing_policy": "Por asesoría. Las primeras 2 horas a precio normal; desde la 3ra hora de la misma asesoría, el costo es a mitad de precio.",
        }
    }
    
    # Si hay comisión, usar Stripe Connect para dividir el pago
    if commission_amount > 0:
        session_data["payment_intent_data"] = {
            "application_fee_amount": commission_amount,
            "transfer_data": {
                "destination": teacher_wallet.stripe_account_id,
                # No especificar amount - Stripe automáticamente transfiere el resto
            },
        }
        
    else:
        # Si no hay comisión (plan premium), transferir todo al docente
        session_data["payment_intent_data"] = {
            "transfer_data": {
                "destination": teacher_wallet.stripe_account_id,
                # No especificar amount - Stripe transfiere el total
            },
        }
       
    
    session = stripe.checkout.Session.create(**session_data)
    return {
        "url": session.url,
        "session_id": session.id,
        "price": total_amount_cents / 100.0
    }

async def calculate_booking_quote(db: AsyncSession, request):
    """
    Calcula cotización pública sin requerir autenticación ni crear sesión Stripe.
    Soporta modo multi-segmentos (request.items) y modo single (availability_id + rango).
    Aplica política global de precios: primeras 2 horas a precio base, desde 3ra hora a precio de hora extra.
    Devuelve desglose por bloques contiguos y totales.
    """
    from app.models.teachers.availability import Availability
    from app.models.teachers.price import Price

    # MULTI-SEGMENTOS
    if getattr(request, "items", None):
        # 1) Cargar disponibilidades y validar mismo docente y materia
        segment_ids = list({int(i.availability_id) for i in request.items})
        seg_avails_result = await db.execute(
            select(Availability).options(joinedload(Availability.user)).where(Availability.id.in_(segment_ids))
        )
        seg_avails = {a.id: a for a in seg_avails_result.scalars().all()}
        if len(seg_avails) != len(segment_ids):
            raise HTTPException(status_code=404, detail="Alguna disponibilidad indicada en 'items' no existe")

        base_avail = seg_avails[segment_ids[0]]
        teacher_id = base_avail.user_id
        preference_id = base_avail.preference_id
        for aid in segment_ids:
            av = seg_avails[aid]
            if av.user_id != teacher_id or av.preference_id != preference_id:
                raise HTTPException(status_code=400, detail="Todas las horas deben ser del mismo docente y misma materia/nivel")

        # 2) Parsear segmentos y validar HH:00, día correcto y que cada segmento no cruce de día
        segments = []
        for it in request.items:
            s = _to_mx_local_naive(it.start_time)
            e = _to_mx_local_naive(it.end_time)
            if (s.minute or s.second or s.microsecond or e.minute or e.second or e.microsecond):
                raise HTTPException(status_code=400, detail="Los horarios deben ser en horas exactas (ej: 09:00, 10:00)")
            if e <= s:
                raise HTTPException(status_code=400, detail="Las horas deben ser positivas y con fin > inicio")
            segments.append({"availability_id": int(it.availability_id), "start": s, "end": e})

        # Día correcto por segmento y mapa de días distintos
        distinct_weekdays = set()
        for seg in segments:
            seg_weekday = seg["start"].weekday() + 1
            if (seg["end"].weekday() + 1) != seg_weekday:
                raise HTTPException(status_code=400, detail="Cada segmento debe estar dentro del mismo día")
            if seg_avails[seg["availability_id"]].day_of_week != seg_weekday:
                raise HTTPException(status_code=400, detail="La fecha seleccionada no corresponde al día de la disponibilidad")
            distinct_weekdays.add(seg_weekday)

        # 3) Validar que CADA hora exista como availability activa por día
        avail_rows_result = await db.execute(
            select(Availability).where(
                Availability.user_id == teacher_id,
                Availability.preference_id == preference_id,
                Availability.day_of_week.in_(distinct_weekdays),
                Availability.is_active == True,
            )
        )
        avail_rows = avail_rows_result.scalars().all()
        day_avail_map = {}
        for r in avail_rows:
            day_avail_map.setdefault(r.day_of_week, set()).add((r.start_time, r.end_time))
        missing = []
        for seg in segments:
            cur = seg["start"]
            seg_weekday = cur.weekday() + 1
            day_set = day_avail_map.get(seg_weekday, set())
            while cur < seg["end"]:
                nxt = cur + timedelta(hours=1)
                if (f"{cur.hour:02d}:00:00", f"{nxt.hour:02d}:00:00") not in day_set:
                    missing.append(f"{cur.strftime('%Y-%m-%d')} {cur.hour:02d}:00-{nxt.hour:02d}:00")
                cur = nxt
        if missing:
            raise HTTPException(status_code=400, detail=f"Las horas seleccionadas no están disponibles: {', '.join(missing)}")

        # 4) Precio y comisión
        price = (await db.execute(select(Price).where(Price.user_id == teacher_id, Price.preference_id == preference_id))).scalar_one_or_none()
        if not price:
            raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")
        commission_rate = await get_teacher_commission_rate(db, teacher_id)

        # 5) Agrupar en bloques contiguos
        segments.sort(key=lambda x: x["start"])
        blocks = []
        b_s, b_e = segments[0]["start"], segments[0]["end"]
        for seg in segments[1:]:
            if seg["start"] == b_e:
                b_e = seg["end"]
            else:
                blocks.append({"start": b_s, "end": b_e})
                b_s, b_e = seg["start"], seg["end"]
        blocks.append({"start": b_s, "end": b_e})

        # 6) Aplicar política por bloque: en CADA bloque, primeras 2 h base; desde la 3ra hora del bloque, extra
        base_cents = int(float(price.selected_prices) * 100)
        extra_cents = int(float(price.extra_hour_price) * 100)

        breakdown = []
        total_amount_cents = 0
        total_hours_all = 0

        for blk in blocks:
            hours = int((blk["end"] - blk["start"]).total_seconds() // 3600)
            if hours <= 0:
                raise HTTPException(status_code=400, detail="Cada bloque debe tener duración positiva en horas")
            block_amount_cents = base_cents * min(hours, 2) + extra_cents * max(0, hours - 2)

            # availability_id del bloque: el segmento que inicia el bloque
            try:
                availability_id_for_block = next(seg["availability_id"] for seg in segments if seg["start"] == blk["start"])  # type: ignore
            except StopIteration:
                availability_id_for_block = segments[0]["availability_id"] if segments else base_avail.id

            breakdown.append({
                "start": blk["start"].isoformat(),
                "end": blk["end"].isoformat(),
                "hours": hours,
                "amount_cents": block_amount_cents,
                "availability_id": int(availability_id_for_block),
            })
            total_amount_cents += block_amount_cents
            total_hours_all += hours

        commission_amount, teacher_amount = calculate_commission_amounts(total_amount_cents, commission_rate)

        return {
            "mode": "multi",
            "teacher_id": teacher_id,
            "preference_id": preference_id,
            "price_id": price.id,
            "base_hour_price_mxn": float(price.selected_prices),
            "extra_hour_price_mxn": float(price.extra_hour_price),
            "global_pricing_policy": "Por asesoría. Las primeras 2 horas a precio normal; desde la 3ra hora de la misma asesoría, el costo es a mitad de precio.",
            "total_hours": total_hours_all,
            "total_amount_cents": total_amount_cents,
            "total_amount_mxn": total_amount_cents / 100.0,
            "commission_rate": commission_rate,
            "commission_amount_cents": commission_amount,
            "teacher_amount_cents": teacher_amount,
            "blocks": breakdown,
        }

    # SINGLE MODE
    # 1) Cargar disponibilidad
    if not request.availability_id or not request.start_time or not request.end_time:
        raise HTTPException(status_code=400, detail="Se requieren availability_id, start_time y end_time para cotización single")
    disponibilidad = (await db.execute(
        select(Availability).options(joinedload(Availability.user)).where(Availability.id == int(request.availability_id))
    )).scalar_one_or_none()
    if not disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    # 2) Fechas y validaciones
    s = _to_mx_local_naive(request.start_time)
    e = _to_mx_local_naive(request.end_time)
    if (s.minute or s.second or s.microsecond or e.minute or e.second or e.microsecond):
        raise HTTPException(status_code=400, detail="Los horarios deben ser en horas exactas (ej: 09:00, 10:00)")
    if e <= s:
        raise HTTPException(status_code=400, detail="Las horas deben ser positivas y con fin > inicio")
    if s.date() != e.date():
        raise HTTPException(status_code=400, detail="La reserva debe estar dentro del mismo día")
    if (s.weekday() + 1) != disponibilidad.day_of_week:
        raise HTTPException(status_code=400, detail="La fecha seleccionada no corresponde al día de la disponibilidad")

    avail_rows_result = await db.execute(
        select(Availability).where(
            Availability.user_id == disponibilidad.user_id,
            Availability.preference_id == disponibilidad.preference_id,
            Availability.day_of_week == (s.weekday() + 1),
            Availability.is_active == True,
        )
    )
    avail_rows = avail_rows_result.scalars().all()
    avail_set = {(row.start_time, row.end_time) for row in avail_rows}
    cur = s
    missing_hours = []
    while cur < e:
        nxt = cur + timedelta(hours=1)
        if (f"{cur.hour:02d}:00:00", f"{nxt.hour:02d}:00:00") not in avail_set:
            missing_hours.append(f"{cur.strftime('%Y-%m-%d')} {cur.hour:02d}:00-{nxt.hour:02d}:00")
        cur = nxt
    if missing_hours:
        raise HTTPException(status_code=400, detail=f"Las horas seleccionadas no están disponibles: {', '.join(missing_hours)}")

    # 3) Precio y comisión
    price = (await db.execute(select(Price).where(Price.user_id == disponibilidad.user_id, Price.preference_id == disponibilidad.preference_id))).scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")
    commission_rate = await get_teacher_commission_rate(db, disponibilidad.user_id)

    # 4) Política global: primeras 2 h base en toda la reserva (single)
    hours_n = int((e - s).total_seconds() // 3600)
    base_cents = int(float(price.selected_prices) * 100)
    extra_cents = int(float(price.extra_hour_price) * 100)
    total_amount_cents = base_cents * min(hours_n, 2) + extra_cents * max(0, hours_n - 2)
    commission_amount, teacher_amount = calculate_commission_amounts(total_amount_cents, commission_rate)

    return {
        "mode": "single",
        "teacher_id": disponibilidad.user_id,
        "preference_id": disponibilidad.preference_id,
        "price_id": (await db.execute(select(Price.id).where(Price.user_id == disponibilidad.user_id, Price.preference_id == disponibilidad.preference_id))).scalar_one(),
        "base_hour_price_mxn": float(price.selected_prices),
        "extra_hour_price_mxn": float(price.extra_hour_price),
        "global_pricing_policy": "Por asesoría. Las primeras 2 horas a precio normal; desde la 3ra hora de la misma asesoría, el costo es a mitad de precio.",
        "total_hours": hours_n,
        "total_amount_cents": total_amount_cents,
        "total_amount_mxn": total_amount_cents / 100.0,
        "commission_rate": commission_rate,
        "commission_amount_cents": commission_amount,
        "teacher_amount_cents": teacher_amount,
        "blocks": [{
            "start": s.isoformat(),
            "end": e.isoformat(),
            "hours": hours_n,
            "amount_cents": total_amount_cents,
            "availability_id": int(request.availability_id),
        }],
    }
