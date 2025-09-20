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


# --- Función auxiliar para actualizar Booking ---
async def update_booking_to_complete(db: AsyncSession, booking_id: int):
    # Obtener el status "complete"
    result = await db.execute(select(Status).where(Status.name == "complete"))
    status = result.scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=500, detail="El status 'complete' no existe en la BD")

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
