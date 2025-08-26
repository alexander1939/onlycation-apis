# Importar las funciones desde los servicios separados
from app.services.bookings.stripe_session_service import create_booking_payment_session
from app.services.bookings.payment_verification_service import verify_booking_payment_and_create_records
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users.user import User
from fastapi import HTTPException

async def get_user_by_token(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user