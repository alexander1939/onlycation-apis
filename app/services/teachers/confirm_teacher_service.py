from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException
from fastapi import UploadFile
import os
import shutil
import uuid

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token

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
    student_id: int,
    payment_booking_id: int,
    evidence_file: UploadFile = None
) -> Confirmation:
    teacher_id = await get_teacher_id_from_token(token)
    await _validate_teacher_exists(db, teacher_id)

    # Buscar confirmación existente
    result = await db.execute(
        select(Confirmation).where(
            Confirmation.payment_booking_id == payment_booking_id
        )
    )
    
    existing_confirmation = result.scalars().first()

    if existing_confirmation:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una confirmación para este paymentbooking."
        )
    confirmation = Confirmation(
        teacher_id=teacher_id,
        student_id=student_id,
        payment_booking_id=payment_booking_id,
        confirmation_date_teacher=confirmation_value
    )

    if confirmation_value is False:
        if not evidence_file:
            raise HTTPException(
                status_code=400,
                detail="Debes subir una evidencia si rechazas la confirmación."
            )
        
        # Guardar archivo con nombre único
        ext = os.path.splitext(evidence_file.filename)[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR_TEACHER, unique_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(evidence_file.file, buffer)

        confirmation.evidence_teacher = unique_name

    db.add(confirmation)
    await db.commit()
    await db.refresh(confirmation)

    return confirmation
