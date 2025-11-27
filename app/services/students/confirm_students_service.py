from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException


from app.models.common.status import Status


from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token
#Notifiacion en la app
from app.services.notifications.notification_service import create_notification

from app.services.notifications.booking_email_service import send_student_confirmation_email

from cryptography.fernet import Fernet
from decouple import config

from datetime import datetime, timedelta, timezone
import pytz
from sqlalchemy.orm import selectinload
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking
from app.models.booking.assessment import Assessment
import os
import shutil
import uuid
from fastapi import UploadFile

from app.services.utils.pagination_service import PaginationService

EVIDENCE_KEY = config("EVIDENCE_ENCRYPTION_KEY")
cipher = Fernet(EVIDENCE_KEY.encode())


UPLOAD_DIR_STUDENT = os.path.join(os.getcwd(), "evidence", "student")
os.makedirs(UPLOAD_DIR_STUDENT, exist_ok=True)




async def _validate_student_exists(db: AsyncSession, student_id: int):
    result = await db.execute(select(User).where(User.id == student_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El estudiante con ID {student_id} no existe")


async def get_student_id_from_token(token: str) -> int:
    payload = verify_token(token)
    student_id = payload.get("user_id")
    if not student_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return student_id


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


async def create_confirmation_by_student(
    db: AsyncSession,
    token: str,
    confirmation_value: bool,
    payment_booking_id: int,
    evidence_file: UploadFile,
    description_student: str
) -> Confirmation:
    student_id = await get_student_id_from_token(token)
    await _validate_student_exists(db, student_id)

    # Buscar PaymentBooking con su Booking
    result = await db.execute(
        select(PaymentBooking)
        .options(selectinload(PaymentBooking.booking).selectinload(Booking.availability))
        .where(PaymentBooking.id == payment_booking_id)
    )
    payment_booking = result.scalar_one_or_none()
    if not payment_booking:
        raise HTTPException(status_code=404, detail="El PaymentBooking no existe")
    booking = payment_booking.booking
    if not booking or not booking.availability:
        raise HTTPException(status_code=400, detail="El booking no tiene disponibilidad asociada")

    teacher_id = booking.availability.user_id
    if not teacher_id:
        raise HTTPException(status_code=400, detail="El booking no tiene docente asignado")

    # Validar ventana de confirmación
    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")
    booking_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
    booking_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
    end_window = booking_end + timedelta(minutes=5)

    if now < booking_start:
        raise HTTPException(status_code=400, detail="La clase aún no ha comenzado.")
    if booking_start <= now < booking_end:
        raise HTTPException(status_code=400, detail="Aún no puedes confirmar. Debes esperar a que termine la clase.")
    if now > end_window:
        raise HTTPException(status_code=400, detail="El tiempo de confirmación expiró.")

    # Validar archivo obligatorio y descripción
    if not evidence_file or not evidence_file.filename:
        raise HTTPException(status_code=400, detail="Es obligatorio subir una evidencia (imagen)")
    if not description_student.strip():
        raise HTTPException(status_code=400, detail="Es obligatorio la descripción")

    # Guardar archivo encriptado
    ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR_STUDENT, unique_name)
    file_bytes = await evidence_file.read()
    encrypted_data = cipher.encrypt(file_bytes)
    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    # --- Buscar o crear Confirmation ---
    result_conf = await db.execute(
        select(Confirmation).where(Confirmation.payment_booking_id == payment_booking_id)
    )
    confirmation = result_conf.scalar_one_or_none()

    if confirmation:
        # Ya existe: verificar si el estudiante ya confirmó
        if confirmation.confirmation_date_student is not None:
            raise HTTPException(status_code=400, detail="El estudiante ya confirmó esta clase.")

        # Actualizar campos del estudiante
        confirmation.student_id = student_id
        confirmation.confirmation_date_student = confirmation_value
        confirmation.evidence_student = unique_name
        confirmation.description_student = description_student
    else:
        # No existe: crear nueva fila
        confirmation = Confirmation(
            teacher_id=teacher_id,
            student_id=student_id,
            payment_booking_id=payment_booking_id,
            confirmation_date_student=confirmation_value,
            evidence_student=unique_name,
            description_student=description_student
        )
        db.add(confirmation)

    await db.commit()
    await db.refresh(confirmation)

    # 🔹 Actualizar el status del Booking solo si ambos confirmaron
    if confirmation.confirmation_date_teacher and confirmation.confirmation_date_student:
        await update_booking_to_complete(db, booking.id)

    # Notificación al docente
    try:
        await create_notification(
            db=db,
            user_id=teacher_id,
            title="Clase confirmada por tu alumno",
            message="El alumno ha confirmado la clase",
            notification_type="student_confirmation"
        )
    except Exception as e:
        print(f"Error creando notificación: {e}")

    # Enviar correo al docente
    try:
        await send_student_confirmation_email(db, teacher_id, payment_booking_id)
    except Exception as e:
        print(f"Error enviando correo: {e}")

    return confirmation



async def get_student_evidence(
    db: AsyncSession,
    token: str,
    confirmation_id: int
) -> tuple[bytes, str]:
    student_id = await get_student_id_from_token(token)

    # Buscar la confirmación que pertenece al estudiante
    result = await db.execute(
        select(Confirmation).where(
            Confirmation.id == confirmation_id,
            Confirmation.student_id == student_id
        )
    )
    confirmation = result.scalar_one_or_none()
    if not confirmation:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la confirmación o no tienes acceso a ella"
        )

    filename = confirmation.evidence_student
    if not filename:
        raise HTTPException(
            status_code=404,
            detail="No existe evidencia registrada para este estudiante"
        )

    file_path = os.path.join(UPLOAD_DIR_STUDENT, filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo de evidencia no existe en el servidor"
        )

    # Leer y desencriptar
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


# ===================== Listados de historial (Alumno) =====================
async def list_student_confirmations_recent(
    db: AsyncSession,
    token: str,
) -> list[dict]:
    """Devuelve SOLO confirmaciones confirmables para el alumno (ventana abierta de 2 horas
    después del fin de la clase), ordenadas por más recientes (fin de clase desc).
    """
    student_id = await get_student_id_from_token(token)

    # Traer pendientes del alumno, ordenadas por fin de clase (desc) y filtrar por ventana en código
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Confirmation, PaymentBooking, Booking)
        .join(PaymentBooking, PaymentBooking.id == Confirmation.payment_booking_id)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .where(Confirmation.student_id == student_id)
        .where(Confirmation.confirmation_date_student.is_(None))
        .order_by(Booking.end_time.desc())
    )
    rows = result.all()

    cdmx_tz = pytz.timezone("America/Mexico_City")
    items: list[dict] = []
    pb_ids = [pb.id for _, pb, _ in rows if pb is not None]
    assessed_set = set()
    if pb_ids:
        res_ass = await db.execute(
            select(Assessment.payment_booking_id)
            .where(Assessment.payment_booking_id.in_(pb_ids))
            .where(Assessment.user_id == student_id)
        )
        assessed_set = {pb_id for (pb_id,) in res_ass.all()}
    for conf, pb, booking in rows:
        b_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
        end_window = b_end + timedelta(hours=2)
        # Saltar clases que aún no terminan
        if now < b_end:
            continue
        # Romper en cuanto la ventana expire (por orden desc, el resto también estará expirado)
        if now > end_window:
            break
        seconds_left = max(int((end_window - now).total_seconds()), 0)
        window_status = "open"
        confirmable_now = True

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
            "confirmable_now": confirmable_now,
            "seconds_left": seconds_left,
            "has_assessment_by_student": (conf.payment_booking_id in assessed_set),
        })

    return items


async def list_student_confirmations_all(
    db: AsyncSession,
    token: str,
    offset: int = 0,
    limit: int = 10,
) -> dict:
    """Lista TODAS las confirmaciones del alumno con paginación usando PaginationService
    (offset/limit). Enriquecemos cada item con tiempos de booking y estado de ventana (2h).
    """
    student_id = await get_student_id_from_token(token)

    page_data = await PaginationService.get_paginated_data(
        db=db,
        model=Confirmation,
        offset=offset,
        limit=limit,
        filters={"student_id": student_id},
    )

    confirmations: list[Confirmation] = page_data["items"]
    if not confirmations:
        return {
            "items": [],
            "total": page_data["total"],
            "offset": offset,
            "limit": limit,
            "has_more": page_data["has_more"],
        }

    # Enriquecer con bookings
    payment_ids = [c.payment_booking_id for c in confirmations]
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
        if not booking:
            continue
        b_start = booking.start_time.astimezone(timezone.utc) if booking.start_time.tzinfo else cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc) if booking.end_time.tzinfo else cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
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
            "payment_created_at": pb_lookup.get(conf.payment_booking_id).created_at if pb_lookup.get(conf.payment_booking_id) else None,
            "booking_start": b_start,
            "booking_end": b_end,
            "confirmed_by_student": conf.confirmation_date_student,
            "confirmed_by_teacher": conf.confirmation_date_teacher,
            "window_status": window_status,
            "confirmable_now": confirmable_now,
            "seconds_left": seconds_left,
        })

    # Ordenar por creación de PaymentBooking desc (más recientes primero)
    items.sort(key=lambda x: (x["payment_created_at"] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

    return {
        "items": items,
        "total": page_data["total"],
        "offset": offset,
        "limit": limit,
        "has_more": page_data["has_more"],
    }


# ====== Utilitario de fecha (local) ======
def _parse_date_str(date_str: str) -> datetime:
    """Parsea fecha en formatos YYYY-MM-DD o DD/MM/YYYY (y YYYY/MM/DD)."""
    from datetime import datetime as dt
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
    last_err = None
    for f in fmts:
        try:
            return dt.strptime(date_str, f)
        except Exception as e:
            last_err = e
    raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {date_str}. Usa YYYY-MM-DD o DD/MM/YYYY.")


# ===================== Filtrado por fecha (Alumno) =====================
async def list_student_confirmations_by_date(
    db: AsyncSession,
    token: str,
    date: str,
) -> list[dict]:
    """Lista confirmaciones del alumno filtradas por la FECHA del booking (día completo).
    La fecha se interpreta en zona America/Mexico_City. Campos opcionales toleran NULLs.
    """
    student_id = await get_student_id_from_token(token)

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
        .where(Confirmation.student_id == student_id)
        .where(Booking.start_time >= start_utc)
        .where(Booking.start_time < next_utc)
        .order_by(Booking.end_time.desc())
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    items: list[dict] = []
    for conf, pb, booking in rows:
        b_start = booking.start_time.astimezone(timezone.utc)
        b_end = booking.end_time.astimezone(timezone.utc)

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
