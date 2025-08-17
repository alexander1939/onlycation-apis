from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException

from app.models.booking.confirmation import Confirmation
from app.models.users.user import User
from app.cores.token import verify_token


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
    payment_booking_id: int
) -> Confirmation:
    student_id = await get_student_id_from_token(token)
    await _validate_student_exists(db, student_id)

    # 🔹 Buscar la confirmación existente (del docente)
    result = await db.execute(
        select(Confirmation).where(Confirmation.payment_booking_id == payment_booking_id)
    )
    confirmation = result.scalars().first()
    if not confirmation:
        raise HTTPException(status_code=404, detail="No existe confirmación previa del docente para este PaymentBooking")

    # 🔹 Actualizar confirmación del estudiante con el student_id del token
    confirmation.student_id = student_id
    confirmation.confirmation_date_student = confirmation_value
    confirmation.updated_at = datetime.utcnow()

    db.add(confirmation)
    await db.commit()
    await db.refresh(confirmation)

    return confirmation
