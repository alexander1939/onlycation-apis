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

# 📧 Servicio de correo
from app.services.notifications.booking_email_service import send_teacher_confirmation_email 

# Cargar la clave de .env
EVIDENCE_KEY = config("EVIDENCE_ENCRYPTION_KEY")
cipher = Fernet(EVIDENCE_KEY.encode())

# Carpeta raíz para evidencia de teacher
UPLOAD_DIR_TEACHER = os.path.join(os.getcwd(), "evidence", "teacher")
os.makedirs(UPLOAD_DIR_TEACHER, exist_ok=True)

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

    # 🔹 Actualizar el status del Booking solo si student también confirmó
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

