from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException
from fastapi import UploadFile
import os
import shutil
import uuid

import pytz 

from cryptography.fernet import Fernet
from decouple import config

from datetime import datetime, timedelta, timezone
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking 

from app.models.common.status import Status  
from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token

#Notifiacion en la app
from app.services.notifications.notification_service import create_notification

# Servicio de correo
from app.services.notifications.booking_email_service import send_teacher_confirmation_email 

# Cargar la clave de .env
EVIDENCE_KEY = config("EVIDENCE_ENCRYPTION_KEY")
cipher = Fernet(EVIDENCE_KEY.encode())

# Carpeta raíz para evidencia de teacher
UPLOAD_DIR_TEACHER = os.path.join(os.getcwd(), "evidence", "teacher")
os.makedirs(UPLOAD_DIR_TEACHER, exist_ok=True)

from app.services.utils.pagination_service import PaginationService
from sqlalchemy import func

async def get_status_id(db: AsyncSession, name: str) -> int:
    result = await db.execute(select(Status).where(Status.name == name))
    status = result.scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=500, detail=f"El status '{name}' no existe en la BD")
    return status.id




async def _validate_teacher_exists(db: AsyncSession, teacher_id: int):
    result = await db.execute(select(User).where(User.id == teacher_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El docente con ID {teacher_id} no existe")


async def get_teacher_id_from_token(token: str) -> int:
    payload = verify_token(token)
    teacher_id = payload.get("user_id")
    if not teacher_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return teacher_id

# --- Función auxiliar para actualizar Booking ---
async def update_booking_to_complete(db: AsyncSession, booking_id: int):
    # Obtener el status "complete"
    result = await db.execute(select(Status).where(Status.name == "completed"))
    status = result.scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=500, detail="El status 'completed' no existe en la BD")

    # Obtener el Booking
    result_bk = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result_bk.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking no encontrado")

    # Actualizar el status
    booking.status_id = status.id
    await db.commit()
    await db.refresh(booking)


async def create_confirmation_by_teacher(
    db: AsyncSession,
    token: str,
    confirmation_value: bool,
    payment_booking_id: int,
    evidence_file: UploadFile,
    description_teacher: str
) -> Confirmation:
    teacher_id = await get_teacher_id_from_token(token)
    await _validate_teacher_exists(db, teacher_id)

    # Buscar PaymentBooking con su Booking
    result = await db.execute(
        select(PaymentBooking, Booking)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .where(PaymentBooking.id == payment_booking_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="El PaymentBooking no existe")
    payment_booking, booking = row

    student_id = booking.user_id
    if not student_id:
        raise HTTPException(status_code=400, detail="El booking no tiene estudiante asignado")

    # Buscar si ya existe confirmación
    existing_confirmation = await db.execute(
        select(Confirmation).where(Confirmation.payment_booking_id == payment_booking_id)
    )
    confirmation = existing_confirmation.scalar_one_or_none()

    if confirmation:
        if confirmation.confirmation_date_teacher is not None:
            raise HTTPException(status_code=400, detail="El docente ya confirmó esta clase.")
        confirmation.teacher_id = teacher_id
        confirmation.confirmation_date_teacher = confirmation_value
    else:
        confirmation = Confirmation(
            teacher_id=teacher_id,
            student_id=student_id,
            payment_booking_id=payment_booking_id,
            confirmation_date_teacher=confirmation_value
        )
        db.add(confirmation)

    # Validar ventana de confirmación
    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")
    booking_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
    booking_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
    end_window = booking_end + timedelta(hours=4)

    if now < booking_start:
        raise HTTPException(status_code=400, detail="La clase aún no ha comenzado.")
    if booking_start <= now < booking_end:
        raise HTTPException(status_code=400, detail="Aún no puedes confirmar. Debes esperar a que termine la clase.")
    if now > end_window:
        raise HTTPException(status_code=400, detail="El tiempo de confirmación expiró.")

    # Validar archivo obligatorio y descripción
    if not evidence_file or not evidence_file.filename:
        raise HTTPException(status_code=400, detail="Es obligatorio subir una evidencia (imagen)")
    if not description_teacher.strip():
        raise HTTPException(status_code=400, detail="Es obligatorio la descripción")

    # Guardar archivo encriptado
    ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR_TEACHER, unique_name)
    file_bytes = await evidence_file.read()
    encrypted_data = cipher.encrypt(file_bytes)
    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    confirmation.evidence_teacher = unique_name
    confirmation.description_teacher = description_teacher

    await db.commit()
    await db.refresh(confirmation)

    # Actualizar el status del Booking solo si student también confirmó
    if confirmation.confirmation_date_teacher and confirmation.confirmation_date_student:
        await update_booking_to_complete(db, booking.id)

    # Notificación
    try:
        await create_notification(
            db=db,
            user_id=student_id,
            title="Clase confirmada por tu docente",
            message="Tu docente ha confirmado la clase",
            notification_type="teacher_confirmation"
        )
    except Exception as e:
        print(f"Error creando notificación: {e}")

    # Correo
    try:
        await send_teacher_confirmation_email(db, student_id, payment_booking_id)
    except Exception as e:
        print(f"Error enviando correo: {e}")

    return confirmation



async def get_teacher_evidence(
    db: AsyncSession,
    token: str,
    confirmation_id: int
) -> tuple[bytes, str]:
    teacher_id = await get_teacher_id_from_token(token)

    # Buscar la confirmación
    result = await db.execute(
        select(Confirmation).where(
            Confirmation.id == confirmation_id,
            Confirmation.teacher_id == teacher_id
        )
    )
    confirmation = result.scalar_one_or_none()
    if not confirmation:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la confirmación o no tienes acceso a ella"
        )

    filename = confirmation.evidence_teacher
    file_path = os.path.join(UPLOAD_DIR_TEACHER, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo de evidencia no existe en el servidor"
        )

    # Leer archivo encriptado y desencriptar
    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    try:
        evidence_bytes = cipher.decrypt(encrypted_data)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al desencriptar la evidencia"
        )

    return evidence_bytes, filename


# ===================== Listados de historial (Docente) =====================
async def list_teacher_confirmations_recent(
    db: AsyncSession,
    token: str,
) -> list[dict]:
    """Devuelve SOLO confirmaciones confirmables para el docente (ventana abierta después del fin
    de la clase), ordenadas por más recientes (fin de clase desc). La ventana se calcula como
    fin_de_clase + 2 horas, en línea con la política actual del servicio de confirmación del docente.
    """
    teacher_id = await get_teacher_id_from_token(token)

    result = await db.execute(
        select(Confirmation, PaymentBooking, Booking)
        .join(PaymentBooking, PaymentBooking.id == Confirmation.payment_booking_id)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .where(Confirmation.teacher_id == teacher_id)
        .where(Confirmation.confirmation_date_teacher.is_(None))
        .order_by(Booking.end_time.desc())
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")
    items: list[dict] = []
    for conf, pb, booking in rows:
        b_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
        end_window = b_end + timedelta(hours=2)
        window_open = now <= end_window
        confirmable_now = (now >= b_end) and window_open
        seconds_left = max(int((end_window - now).total_seconds()), 0)
        window_status = "open"

        items.append({
            "id": conf.id,
            "teacher_id": conf.teacher_id,
            "student_id": conf.student_id,
            "payment_booking_id": conf.payment_booking_id,
            "payment_created_at": pb.created_at,
            "booking_start": b_start,
            "booking_end": b_end,
            "confirmed_by_student": conf.confirmation_date_student,
            "confirmed_by_teacher": conf.confirmation_date_teacher,
            "window_status": window_status,
            "confirmable_now": True,
            "seconds_left": seconds_left,
        })

    return items


async def list_teacher_confirmations_all(
    db: AsyncSession,
    token: str,
    offset: int = 0,
    limit: int = 10,
) -> dict:
    """Lista TODAS las confirmaciones del docente, paginando directamente desde la
    tabla Confirmation para NO perder filas cuando falten relaciones.
    """
    teacher_id = await get_teacher_id_from_token(token)

    # Total exacto desde confirmations
    total_result = await db.execute(
        select(func.count(Confirmation.id)).where(Confirmation.teacher_id == teacher_id)
    )
    total = total_result.scalar() or 0

    # Página desde confirmations (orden por creación más reciente)
    result_conf = await db.execute(
        select(Confirmation)
        .where(Confirmation.teacher_id == teacher_id)
        .order_by(Confirmation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    confirmations: list[Confirmation] = result_conf.scalars().all()

    if not confirmations:
        return {
            "items": [],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
        }

    # Enriquecer con PaymentBooking y Booking si existen, pero sin descartar filas
    payment_ids = [c.payment_booking_id for c in confirmations if c.payment_booking_id]
    pb_to_booking = {}
    pb_lookup = {}
    if payment_ids:
        result = await db.execute(
            select(PaymentBooking, Booking)
            .join(Booking, Booking.id == PaymentBooking.booking_id)
            .where(PaymentBooking.id.in_(payment_ids))
        )
        rows = result.all()
        pb_to_booking = {pb.id: bk for pb, bk in rows}
        pb_lookup = {pb.id: pb for pb, _ in rows}

    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")
    items: list[dict] = []
    for conf in confirmations:
        booking = pb_to_booking.get(conf.payment_booking_id)
        pb_obj = pb_lookup.get(conf.payment_booking_id)
        payment_created_at = pb_obj.created_at if pb_obj else None

        if booking:
            b_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
            b_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
            end_window = b_end + timedelta(hours=4)
            window_open = now <= end_window
            confirmable_now = (now >= b_end) and window_open
            seconds_left = max(int((end_window - now).total_seconds()), 0) if window_open else 0
            window_status = "open" if window_open else "expired"
        else:
            b_start = None
            b_end = None
            window_status = None
            confirmable_now = None
            seconds_left = None

        items.append({
            "id": conf.id,
            "teacher_id": conf.teacher_id,
            "student_id": conf.student_id,
            "payment_booking_id": conf.payment_booking_id,
            "payment_created_at": payment_created_at,
            "booking_start": b_start,
            "booking_end": b_end,
            "confirmed_by_student": conf.confirmation_date_student,
            "confirmed_by_teacher": conf.confirmation_date_teacher,
            "window_status": window_status,
            "confirmable_now": confirmable_now,
            "seconds_left": seconds_left,
        })

    has_more = (offset + limit) < total

    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
    }

# ============== Detalle de confirmación (Docente/Alumno) ==============
async def get_confirmation_detail(
    db: AsyncSession,
    token: str,
    confirmation_id: int,
) -> dict:
    """Devuelve el detalle de una confirmación específica para el usuario autenticado
    (ya sea docente o alumno). Retorna campos opcionales en None cuando faltan relaciones.
    """
    payload = verify_token(token)
    viewer_id = payload.get("user_id")
    if not viewer_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")

    # Obtener la confirmación
    result = await db.execute(select(Confirmation).where(Confirmation.id == confirmation_id))
    conf = result.scalar_one_or_none()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmación no encontrada")

    # Autorización: solo teacher o student dueño de la confirmación
    if viewer_id not in (conf.teacher_id, conf.student_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta confirmación")

    # Cargar PaymentBooking y Booking si existen
    booking = None
    pb = None
    if conf.payment_booking_id:
        res_pb = await db.execute(select(PaymentBooking).where(PaymentBooking.id == conf.payment_booking_id))
        pb = res_pb.scalar_one_or_none()
        if pb and pb.booking_id:
            res_bk = await db.execute(select(Booking).where(Booking.id == pb.booking_id))
            booking = res_bk.scalar_one_or_none()

    # Normalizar tiempos a UTC (si existen)
    b_start = None
    b_end = None
    if booking:
        cdmx_tz = pytz.timezone("America/Mexico_City")
        b_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)

    return {
        "id": conf.id,
        "teacher_id": conf.teacher_id,
        "student_id": conf.student_id,
        "payment_booking_id": conf.payment_booking_id,
        "booking_start": b_start,
        "booking_end": b_end,
        "confirmed_by_student": conf.confirmation_date_student,
        "confirmed_by_teacher": conf.confirmation_date_teacher,
        "evidence_student": conf.evidence_student,
        "evidence_teacher": conf.evidence_teacher,
        "description_student": conf.description_student,
        "description_teacher": conf.description_teacher,
    }

def _parse_date_str(date_str: str) -> datetime:
    """Parse a date string that could come as YYYY-MM-DD or DD/MM/YYYY.
    Returns a naive datetime at 00:00:00 (local date components).
    """
    from datetime import datetime as dt
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
    last_err = None
    for f in fmts:
        try:
            return dt.strptime(date_str, f)
        except Exception as e:
            last_err = e
    raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {date_str}. Usa YYYY-MM-DD o DD/MM/YYYY.")

async def list_teacher_confirmations_by_date(
    db: AsyncSession,
    token: str,
    date: str,
) -> list[dict]:
    """Lista confirmaciones del docente filtradas por la FECHA del booking (día completo).
    La fecha se interpreta en zona America/Mexico_City. Se incluyen campos opcionales si faltan relaciones.
    """
    teacher_id = await get_teacher_id_from_token(token)

    # Calcular rango de día [start_local, next_day_local) en MX y convertir a UTC
    base = _parse_date_str(date)
    cdmx_tz = pytz.timezone("America/Mexico_City")
    start_local = cdmx_tz.localize(datetime(base.year, base.month, base.day, 0, 0, 0))
    next_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    next_utc = next_local.astimezone(timezone.utc)

    # Traer confirmaciones asociadas a bookings cuyo start_time caiga en ese día local
    result = await db.execute(
        select(Confirmation, PaymentBooking, Booking)
        .join(PaymentBooking, PaymentBooking.id == Confirmation.payment_booking_id)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .where(Confirmation.teacher_id == teacher_id)
        .where(Booking.start_time >= start_utc)
        .where(Booking.start_time < next_utc)
        .order_by(Booking.end_time.desc())
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    items: list[dict] = []
    for conf, pb, booking in rows:
        # Normalizar a UTC por consistencia de salida
        b_start = booking.start_time.astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc)

        # Ventana 2h (opcional, informativa)
        end_window = b_end + timedelta(hours=2)
        window_open = now <= end_window
        confirmable_now = (now >= b_end) and window_open
        seconds_left = max(int((end_window - now).total_seconds()), 0) if window_open else 0
        window_status = "open" if window_open else "expired"

        items.append({
            "id": conf.id,
            "teacher_id": conf.teacher_id,
            "student_id": conf.student_id,
            "payment_booking_id": conf.payment_booking_id,
            "payment_created_at": pb.created_at if pb else None,
            "booking_start": b_start,
            "booking_end": b_end,
            "confirmed_by_student": conf.confirmation_date_student,
            "confirmed_by_teacher": conf.confirmation_date_teacher,
            "window_status": window_status,
            "confirmable_now": confirmable_now,
            "seconds_left": seconds_left,
        })

    return items
