from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token


import os
import shutil
import uuid
from fastapi import UploadFile


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
    evidence_file: UploadFile = None
) -> Confirmation:
    student_id = await get_student_id_from_token(token)
    await _validate_student_exists(db, student_id)

    result = await db.execute(
        select(Confirmation).where(Confirmation.payment_booking_id == payment_booking_id)
    )
    confirmation = result.scalars().first()
    if not confirmation:
        raise HTTPException(
            status_code=404,
            detail="No existe confirmación previa del docente para este PaymentBooking"
        )

    # 🔹 Bloquear si el estudiante ya confirmó antes (True o False)
    if confirmation.confirmation_date_student is not None:
        raise HTTPException(
            status_code=400,
            detail="El estudiante ya realizó una confirmación y no puede modificarla."
        )

    # 🔹 Bloquear si el PaymentBooking ya está asociado a otro estudiante
    if confirmation.student_id and confirmation.student_id != student_id:
        raise HTTPException(
            status_code=403,
            detail="Este PaymentBooking ya tiene un estudiante diferente asignado."
        )

    # 🔹 Si el estudiante rechaza, debe subir evidencia
    if confirmation_value is False:
        if not evidence_file:
            raise HTTPException(
                status_code=400,
                detail="Debes subir una evidencia si rechazas la confirmación."
            )

        # Bloquear si ya existe evidencia guardada
        if confirmation.evidence_student:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una evidencia registrada para esta confirmación."
            )

        # Guardar archivo con nombre único
        ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR_STUDENT, unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(evidence_file.file, buffer)

        confirmation.evidence_student = unique_name

    # 🔹 Guardar confirmación
    confirmation.student_id = student_id
    confirmation.confirmation_date_student = confirmation_value
    confirmation.updated_at = datetime.utcnow()

    db.add(confirmation)
    await db.commit()
    await db.refresh(confirmation)

    return confirmation