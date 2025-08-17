from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.teachers.confirm_teacher_schema import ConfirmationCreateRequest

# ==================== VALIDACIONES ====================

async def _validate_teacher_exists(db: AsyncSession, teacher_id: int):
    result = await db.execute(select(User).where(User.id == teacher_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El docente con ID {teacher_id} no existe")

# ==================== FUNCIONES PRINCIPALES ====================

async def get_teacher_id_from_token(token: str) -> int:
    payload = verify_token(token)
    teacher_id = payload.get("user_id")  # Asegúrate de que tu token guarde el ID aquí
    if not teacher_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return teacher_id

async def create_confirmation_by_teacher(
    db: AsyncSession,
    token: str,
    confirmation_value: bool,
    student_id: int,
    payment_booking_id: int
) -> Confirmation:
    teacher_id = await get_teacher_id_from_token(token)
    await _validate_teacher_exists(db, teacher_id)

    db_confirmation = Confirmation(
        teacher_id=teacher_id,
        student_id=student_id,
        payment_booking_id=payment_booking_id,
        confirmation_date_teacher=confirmation_value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_confirmation)
    await db.commit()
    await db.refresh(db_confirmation)

    return db_confirmation
