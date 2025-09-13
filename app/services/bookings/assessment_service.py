from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, func
from datetime import datetime
from fastapi import HTTPException, status

from app.models.booking.assessment import Assessment
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.users import User  # asegúrate que tu modelo User exista y tenga "name"


# Crear un assessment
async def create_assessment(db: AsyncSession, user_id: int, data):
    # 1. Verificar que el payment_booking existe
    stmt_payment = select(PaymentBooking).where(PaymentBooking.id == data.payment_booking_id)
    result = await db.execute(stmt_payment)
    payment_booking = result.scalar_one_or_none()

    if not payment_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe la reserva asociada al pago."
        )

    # 2. Validar que el user_id del payment_booking coincide con el usuario logueado
    if payment_booking.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para evaluar esta reserva."
        )

    # 3. Validar que este payment_booking_id no haya sido evaluado antes
    stmt_existing = select(Assessment).where(Assessment.payment_booking_id == data.payment_booking_id)
    result_existing = await db.execute(stmt_existing)
    existing_assessment = result_existing.first()

    if existing_assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta reserva ya ha sido evaluada."
        )

    # 4. Crear el assessment si pasa todas las validaciones
    stmt = insert(Assessment).values(
        user_id=user_id,
        payment_booking_id=data.payment_booking_id,
        qualification=data.qualification,
        comment=data.comment,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ).returning(Assessment)

    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def get_teacher_comments_service(db: AsyncSession, teacher_id: int):
    query = (
        select(
            Assessment.id,
            Assessment.comment,
            Assessment.qualification,
            User.id.label("student_id"),
            func.concat(User.first_name, " ", User.last_name).label("student_name"),  # ✅ corrección aquí
        )
        .join(PaymentBooking, PaymentBooking.id == Assessment.payment_booking_id)
        .join(Booking, Booking.id == PaymentBooking.booking_id)
        .join(Availability, Availability.id == Booking.availability_id)
        .join(User, User.id == Assessment.user_id)  # este User es el alumno
        .where(Availability.user_id == teacher_id)  # docente autenticado
    )

    result = await db.execute(query)
    comments = result.mappings().all()

    if not comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron comentarios para este docente"
        )

    return comments