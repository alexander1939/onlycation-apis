from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from datetime import datetime, timedelta

from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.common.status import Status
from app.models.users.user import User
from app.models.teachers.availability import Availability
from app.external.stripe_config import stripe
from app.services.notifications.booking_notification_service import (
    send_booking_confirmation_to_student,
    send_booking_notification_to_teacher,
    send_payment_confirmation_notification
)
from app.services.notifications.booking_email_service import (
    send_booking_confirmation_email,
    send_payment_confirmation_email,
    send_new_booking_email_to_teacher
)
from app.services.bookings.room_service import generate_secure_room_link

async def get_active_status(db: AsyncSession):
    result = await db.execute(select(Status).where(Status.name == "active"))
    return result.scalar_one_or_none()

async def verify_booking_payment_and_create_records(db: AsyncSession, session_id: str, user_id: int):
    # Obtener sesión de Stripe
    session = stripe.checkout.Session.retrieve(session_id)
    payment_intent_id = session.payment_intent

    if session.metadata.get("user_id") != str(user_id):
        raise HTTPException(status_code=403, detail="No tienes permisos para verificar esta sesión")
    if session.payment_status != "paid":
        raise HTTPException(status_code=400, detail="Pago no completado")

    # Validar que no se haya procesado antes usando el payment_intent_id específico
    existing_payment = await db.execute(
        select(PaymentBooking).where(
            PaymentBooking.stripe_payment_intent_id == payment_intent_id
        )
    )
    if existing_payment.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pago ya fue procesado anteriormente")

    # Convierte los strings a datetime
    start_time_raw = session.metadata["start_time"]
    end_time_raw = session.metadata["end_time"]

    def parse_datetime(val):
        if isinstance(val, str) and val.isdigit():
            return datetime.fromtimestamp(int(val))
        return datetime.fromisoformat(val)

    start_time = parse_datetime(start_time_raw)
    end_time = parse_datetime(end_time_raw)

    # Crear Booking
    booking = Booking(
        user_id=user_id,
        availability_id=int(session.metadata["availability_id"]),
        start_time=start_time,
        end_time=end_time,
        class_space="",  # Se asignará después
        status_id=(await get_active_status(db)).id
    )
    db.add(booking)
    await db.flush()

    # Crear room_name seguro y único después de tener el booking.id
    teacher_id = int(session.metadata["teacher_id"])
    class_link, room_name = generate_secure_room_link(booking.id, teacher_id, user_id, start_time)
    booking.class_space = class_link

    # Recarga el booking con la relación availability y user
    booking_result = await db.execute(
        select(Booking).options(
            joinedload(Booking.availability).joinedload(Availability.user)
        ).where(Booking.id == booking.id)
    )
    booking = booking_result.scalar_one()

    # Obtener datos del usuario (estudiante) y del docente antes de crear detalles
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one()
    
    # Obtener datos del docente desde la relación ya cargada
    teacher_name = f"{booking.availability.user.first_name} {booking.availability.user.last_name}"

    # Obtener datos de comisión desde metadata
    commission_rate = float(session.metadata.get("commission_rate", "60.00"))
    commission_amount = int(session.metadata.get("commission_amount", "0"))
    teacher_amount = int(session.metadata.get("teacher_amount", "0"))
    teacher_stripe_account_id = session.metadata.get("teacher_stripe_account_id")
    
    # Calcular fecha de transferencia (15 días después de la clase)
    transfer_date = end_time + timedelta(days=15)
    
    # Crear PaymentBooking con todos los campos de comisión
    payment_booking = PaymentBooking(
        user_id=user_id,
        booking_id=booking.id,
        price_id=int(session.metadata["price_id"]),
        total_amount=int(session.amount_total),  # En centavos
        commission_percentage=commission_rate,
        commission_amount=commission_amount,
        teacher_amount=teacher_amount,
        platform_amount=commission_amount,  # La comisión es lo que recibe la plataforma
        transfer_date=transfer_date,
        transfer_status="pending",
        teacher_stripe_account_id=teacher_stripe_account_id,
        application_fee_amount=commission_amount if commission_amount > 0 else None,
        status_id=(await get_active_status(db)).id,
        stripe_payment_intent_id=payment_intent_id
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
    booking_details = {
        'booking_id': booking.id,
        'date': booking.start_time.strftime('%d/%m/%Y %H:%M'),
        'start_date': booking.start_time.strftime('%d/%m/%Y %H:%M'),
        'end_date': booking.end_time.strftime('%d/%m/%Y %H:%M'),
        'student_name': f"{user.first_name} {user.last_name}",
        'teacher_name': teacher_name
    }
    
    payment_details = {
        'payment_id': payment_booking.id,
        'amount': payment_booking.total_amount
    }
    
    # Obtener teacher_id antes del commit para evitar problemas de sesión
    teacher_id = booking.availability.user_id
    
    # Notificar al estudiante sobre confirmación de reserva
    await send_booking_confirmation_to_student(db, user_id, booking_details)
    
    # Notificar al estudiante sobre confirmación de pago
    await send_payment_confirmation_notification(db, user_id, payment_details)
    
    # Notificar al docente sobre nueva reserva
    await send_booking_notification_to_teacher(db, teacher_id, booking_details)
    
    # Enviar emails con información detallada
    await send_booking_confirmation_email(db, user_id, booking_details)
    await send_payment_confirmation_email(db, user_id, payment_details)
    await send_new_booking_email_to_teacher(db, teacher_id, booking_details)

    await db.commit()

    return {
        "booking_id": booking.id,
        "payment_booking_id": payment_booking.id,
        "confirmation_id": confirmation.id,
        "payment_status": session.payment_status
    }
