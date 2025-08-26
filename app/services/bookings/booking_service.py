from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.teachers.price import Price
from app.models.users.user import User
from app.models.common.status import Status
from app.external.stripe_config import stripe
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.teachers.availability import Availability
from app.services.notifications.notification_service import create_booking_payment_notification, create_teacher_booking_notification

async def get_active_status(db: AsyncSession):
    result = await db.execute(select(Status).where(Status.name == "active"))
    return result.scalar_one_or_none()

async def create_booking_payment_session(db: AsyncSession, user: User, booking_data):
    # 1. Validar que la disponibilidad existe
    disponibilidad_result = await db.execute(
        select(Availability).where(Availability.id == booking_data.availability_id)
    )
    disponibilidades = disponibilidad_result.scalars().all()
    if disponibilidades:
        disponibilidad = disponibilidades[0]  # O elige la que corresponda
    else:
        disponibilidad = None

    if not disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    # 2. Validar que el horario solicitado está dentro del rango del docente
    if not (disponibilidad.start_time <= booking_data.start_time < booking_data.end_time <= disponibilidad.end_time):
        raise HTTPException(
            status_code=400,
            detail="El horario solicitado no está dentro del rango de disponibilidad del docente"
        )

    # 3. Validar que no hay traslape con otra reserva ya existente
    overlap_result = await db.execute(
        select(Booking).where(
            Booking.availability_id == booking_data.availability_id,
            Booking.start_time < booking_data.end_time,
            Booking.end_time > booking_data.start_time
        )
    )
    if overlap_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ya existe una reserva para ese horario"
        )

    price = await db.get(Price, booking_data.price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Precio no encontrado")

    total_hours = booking_data.total_hours
    if total_hours < 1:
        raise HTTPException(status_code=400, detail="Debes reservar al menos una hora")

    line_items = [{
        "price": price.stripe_price_id,
        "quantity": 1
    }]
    if total_hours > 1:
        line_items.append({
            "price": price.stripe_extra_price_id,  # Asegúrate de tener este campo en tu modelo Price
            "quantity": total_hours - 1
        })

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        customer_email=user.email,
        line_items=line_items,
        success_url="http://localhost:5173/?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://localhost:5173/",
        metadata={
            "user_id": str(user.id),
            "price_id": str(price.id),
            "availability_id": str(booking_data.availability_id),
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "total_hours": str(total_hours)
        }
    )
    return {
        "url": session.url,
        "session_id": session.id,
        "price": price.selected_prices + (total_hours - 1) * price.extra_hour_price
    }

async def verify_booking_payment_and_create_records(db: AsyncSession, session_id: str, user_id: int):
    # Obtener sesión de Stripe
    session = stripe.checkout.Session.retrieve(session_id)
    payment_intent_id = session.payment_intent  # <-- Aquí obtienes el PaymentIntent ID

    if session.metadata.get("user_id") != str(user_id):
        raise HTTPException(status_code=403, detail="No tienes permisos para verificar esta sesión")
    if session.payment_status != "paid":
        return {
            "success": False,
            "message": "Pago no completado",
            "payment_status": session.payment_status
        }

    # Validar que no se haya procesado antes
    existing_payment = await db.execute(
        select(PaymentBooking).where(
            PaymentBooking.user_id == user_id,
            PaymentBooking.created_at >= datetime.fromtimestamp(session.created)
        )
    )
    if existing_payment.scalar_one_or_none():
        return {
            "success": True,
            "message": "Pago ya fue procesado anteriormente",
            "payment_status": session.payment_status
        }

    # Convierte los strings a datetime
    start_time_raw = session.metadata["start_time"]
    end_time_raw = session.metadata["end_time"]

    def parse_datetime(val):
        if isinstance(val, str) and val.isdigit():
            return datetime.fromtimestamp(int(val))
        return datetime.fromisoformat(val)

    start_time = parse_datetime(start_time_raw)
    end_time = parse_datetime(end_time_raw)

    room_name = f"class-{booking.id}-{user_id}"
    class_link = f"https://meet.jit.si/{room_name}"

    # Crear Booking
    booking = Booking(
        user_id=user_id,
        availability_id=int(session.metadata["availability_id"]),
        start_time=start_time,
        end_time=end_time,
        class_space=class_link,
        status_id=(await get_active_status(db)).id
    )
    db.add(booking)
    await db.flush()

    


    # Recarga el booking con la relación availability
    booking_result = await db.execute(
        select(Booking).options(joinedload(Booking.availability)).where(Booking.id == booking.id)
    )
    booking = booking_result.scalar_one()

    # Crear PaymentBooking
    payment_booking = PaymentBooking(
        user_id=user_id,
        booking_id=booking.id,
        price_id=int(session.metadata["price_id"]),
        total_amount=int(session.amount_total / 100),
        status_id=(await get_active_status(db)).id,
        stripe_payment_intent_id=payment_intent_id  # <-- Lo guardas aquí
    )
    db.add(payment_booking)
    await db.flush()

    # Crear Confirmation (confirmación)
    confirmation = Confirmation(
        teacher_id=booking.availability.user_id,
        student_id=user_id,
        payment_booking_id=payment_booking.id
    )
    db.add(confirmation)
    await create_booking_payment_notification(db, user_id, payment_booking.id)
    # Crear notificación para el profesor
    await create_teacher_booking_notification(
        db,
        teacher_id=booking.availability.user_id,
        booking_id=booking.id,
        start_time=start_time,
        end_time=end_time
    )

    await db.commit()

    return {
        "success": True,
        "message": "Pago verificado y reserva creada",
        "payment_status": session.payment_status,
        "data": {
            "booking_id": booking.id,
            "payment_booking_id": payment_booking.id,
            "confirmation_id": confirmation.id
        }
    }


async def get_user_by_token(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user