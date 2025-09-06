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

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token

# Cargar la clave de .env
EVIDENCE_KEY = config("EVIDENCE_ENCRYPTION_KEY")
cipher = Fernet(EVIDENCE_KEY.encode())

# Carpeta raíz para evidencia de teacher
UPLOAD_DIR_TEACHER = os.path.join(os.getcwd(), "evidence", "teacher")
os.makedirs(UPLOAD_DIR_TEACHER, exist_ok=True)


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


async def create_confirmation_by_teacher(
    db: AsyncSession,
    token: str,
    confirmation_value: bool,
    #student_id: int,
    payment_booking_id: int,
    evidence_file: UploadFile,  # obligatorio
    description_teacher: str
) -> Confirmation:
    teacher_id = await get_teacher_id_from_token(token)
    await _validate_teacher_exists(db, teacher_id)

    # Buscar PaymentBooking
    result = await db.execute(
        select(PaymentBooking, Booking)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .where(PaymentBooking.id == payment_booking_id)
    )
    payment_booking, booking = result.first()
    if not payment_booking:
        raise HTTPException(status_code=404, detail="El PaymentBooking no existe")
    
    student_id = booking.user_id
    if not student_id:
        raise HTTPException(status_code=400, detail="El booking no tiene estudiante asignado")

    booking = payment_booking.booking
    if not booking:
        raise HTTPException(status_code=404, detail="No se encontró el Booking asociado")

    # 🚨 Validar si el docente ya confirmó antes este booking
    existing_confirmation = await db.execute(
        select(Confirmation).where(
            Confirmation.teacher_id == teacher_id,
            Confirmation.payment_booking_id == payment_booking_id
        )
    )
    if existing_confirmation.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ya realizaste una confirmación para esta clase. Solo se permite una por docente."
        )

    # Validar ventana de confirmación: solo 5 min después del end_time
        # 🚨 Validar ventana de confirmación
    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")

    # Normalizar fechas con tz
    if booking.start_time.tzinfo is None:
        booking_start = cdmx_tz.localize(booking.start_time).astimezone(timezone.utc)
    else:
        booking_start = booking.start_time.astimezone(timezone.utc)

    if booking.end_time.tzinfo is None:
        booking_end = cdmx_tz.localize(booking.end_time).astimezone(timezone.utc)
    else:
        booking_end = booking.end_time.astimezone(timezone.utc)
    

    start_window = booking_end
    end_window = booking_end + timedelta(minutes=5)

    # 🚨 Validaciones
    if now < booking_start:
        raise HTTPException(
            status_code=400,
            detail="La clase aún no ha comenzado."
        )
    if booking_start <= now < booking_end:
        raise HTTPException(
            status_code=400,
            detail="Aún no puedes confirmar. Debes esperar a que termine la clase."
        )
    if now > end_window:
        raise HTTPException(
            status_code=400,
            detail="El tiempo de confirmación expiró."
        )

    # Validar archivo obligatorio
    if not evidence_file or not evidence_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Es obligatorio subir una evidencia (imagen)"
        )

    # Validar descripción
    if not description_teacher.strip():
        raise HTTPException(
            status_code=400,
            detail="Es obligatorio la descripción"
        )

    # Guardar archivo encriptado con nombre único
    ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}" 
    file_path = os.path.join(UPLOAD_DIR_TEACHER, unique_name)

    file_bytes = await evidence_file.read()
    encrypted_data = cipher.encrypt(file_bytes)

    with open(file_path, "wb") as f:
        f.write(encrypted_data)




    # Crear confirmación
    confirmation = Confirmation(
        teacher_id=teacher_id,
        student_id=student_id,
        payment_booking_id=payment_booking_id,
        confirmation_date_teacher=confirmation_value,
        evidence_teacher=unique_name,
        description_teacher=description_teacher
    )

    db.add(confirmation)
    await db.commit()
    await db.refresh(confirmation)

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
