from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token


from cryptography.fernet import Fernet
from decouple import config

from datetime import datetime, timedelta, timezone
import pytz
from sqlalchemy.orm import selectinload
from app.models.booking.payment_bookings import PaymentBooking

import os
import shutil
import uuid
from fastapi import UploadFile


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


async def create_confirmation_by_student(
    db: AsyncSession,
    token: str,
    confirmation_value: bool,
    payment_booking_id: int,
    evidence_file: UploadFile = None,
    description_student: str = None
) -> Confirmation:
    student_id = await get_student_id_from_token(token)
    await _validate_student_exists(db, student_id)

    # 🔹 Cargamos confirmation junto con payment_booking y booking
    result = await db.execute(
        select(Confirmation)
        .options(
            selectinload(Confirmation.payment_booking).selectinload(PaymentBooking.booking)
        )
        .where(Confirmation.payment_booking_id == payment_booking_id)
    )
    confirmation = result.scalar_one_or_none()
    if not confirmation:
        raise HTTPException(
            status_code=404,
            detail="No existe confirmación previa del docente para este PaymentBooking"
        )

    # 🚨 Bloquear si el estudiante ya confirmó antes (True o False)
    if confirmation.confirmation_date_student is not None:
        raise HTTPException(
            status_code=400,
            detail="El estudiante ya realizó una confirmación y no puede modificarla."
        )

    # 🚨 Bloquear si ya está asociado a otro estudiante
    if confirmation.student_id and confirmation.student_id != student_id:
        raise HTTPException(
            status_code=403,
            detail="Este PaymentBooking ya tiene un estudiante diferente asignado."
        )

    # 🚨 Validación de ventana de tiempo
        # 🚨 Validación de ventana de tiempo
    now = datetime.now(timezone.utc)
    cdmx_tz = pytz.timezone("America/Mexico_City")

    booking = confirmation.payment_booking.booking  # ahora ya está en memoria

    # Normalizar fechas con zona horaria
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

    # 🚨 Nueva validación
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


    # 🚨 Validar evidencia y descripción SOLO si confirmation = True
    if not evidence_file or not evidence_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Es obligatorio subir la evidencia"
        )
    if not description_student or not description_student.strip():
        raise HTTPException(
            status_code=400,
            detail="Es obligatorio escribir una descripción"
        )

        # Bloquear si ya existe evidencia guardada
    if confirmation.evidence_student:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una evidencia registrada para esta confirmación."
        )

        # Guardar archivo
    ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR_STUDENT, unique_name)

    file_byte = await evidence_file.read()
    encrypted_date = cipher.encrypt(file_byte)

    with open(file_path, "wb") as f:
        f.write(encrypted_date)

    confirmation.evidence_student = unique_name
    confirmation.description_student = description_student

   
    confirmation.student_id = student_id
    confirmation.confirmation_date_student = confirmation_value
    confirmation.updated_at = datetime.utcnow()

    db.add(confirmation)
    await db.commit()
    await db.refresh(confirmation)

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
