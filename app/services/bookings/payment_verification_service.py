from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from datetime import datetime, timedelta
import json

from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.common.status import Status
from app.models.users.user import User
from app.models.teachers.availability import Availability
from app.external.stripe_config import stripe
from app.services.bookings.commission_service import calculate_commission_amounts
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

    # Idempotencia: si YA existen pagos con este intent, devolverlos
    existing_payments_result = await db.execute(
        select(PaymentBooking).options(joinedload(PaymentBooking.booking)).where(
            PaymentBooking.stripe_payment_intent_id == payment_intent_id
        )
    )
    existing_payments = existing_payments_result.scalars().all()
    if existing_payments:
        booking_ids = [pb.booking_id for pb in existing_payments]
        payment_ids = [pb.id for pb in existing_payments]
        confs_result = await db.execute(
            select(Confirmation.id).where(Confirmation.payment_booking_id.in_(payment_ids))
        )
        confirmation_ids = [c.id for c in confs_result.scalars().all()]
        return {
            "bookings": booking_ids,
            "payment_bookings": payment_ids,
            "confirmations": confirmation_ids,
            "payment_status": session.payment_status,
        }

    # Multi-segmento: manejar bloques/segmentos y no leer start_time/end_time
    booking_mode = session.metadata.get("booking_mode", "single")
    if booking_mode == "multi" or session.metadata.get("blocks"):
        try:
            blocks = json.loads(session.metadata.get("blocks", "[]"))
            segments = json.loads(session.metadata.get("segments", "[]"))
        except Exception:
            raise HTTPException(status_code=400, detail="Metadata inválida para reservas múltiples")

        if not blocks:
            raise HTTPException(status_code=400, detail="No hay bloques para crear reservas múltiples")

        teacher_id = int(session.metadata.get("teacher_id"))
        price_id = int(session.metadata.get("price_id"))
        commission_rate = float(session.metadata.get("commission_rate", "60.00"))
        teacher_stripe_account_id = session.metadata.get("teacher_stripe_account_id")

        def find_availability_for_block(b_start_iso: str) -> int:
            b_start = datetime.fromisoformat(b_start_iso)
            for seg in segments:
                s = datetime.fromisoformat(seg["start_time"]) if isinstance(seg["start_time"], str) else seg["start_time"]
                if s == b_start:
                    return int(seg["availability_id"])
            return int(segments[0]["availability_id"]) if segments else 0

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()
        active_status = await get_active_status(db)

        created_booking_ids = []
        created_payment_ids = []
        created_confirmation_ids = []

        for blk in blocks:
            b_start = datetime.fromisoformat(blk["start_time"]) if isinstance(blk["start_time"], str) else blk["start_time"]
            b_end = datetime.fromisoformat(blk["end_time"]) if isinstance(blk["end_time"], str) else blk["end_time"]
            block_amount_cents = int(blk.get("amount_cents", 0))
            availability_id = find_availability_for_block(blk["start_time"]) if isinstance(blk["start_time"], str) else find_availability_for_block(blk["start_time"].isoformat())

            booking = Booking(
                user_id=user_id,
                availability_id=availability_id,
                start_time=b_start,
                end_time=b_end,
                class_space="",
                status_id=active_status.id,
            )
            db.add(booking)
            await db.flush()

            class_link, room_name = generate_secure_room_link(booking.id, teacher_id, user_id, b_start)
            booking.class_space = class_link

            booking_loaded = (await db.execute(
                select(Booking).options(joinedload(Booking.availability).joinedload(Availability.user)).where(Booking.id == booking.id)
            )).scalar_one()
            teacher_name = f"{booking_loaded.availability.user.first_name} {booking_loaded.availability.user.last_name}"

            commission_amount, teacher_amount = calculate_commission_amounts(block_amount_cents, commission_rate)
            transfer_date = b_end + timedelta(days=15)

            payment_booking = PaymentBooking(
                user_id=user_id,
                booking_id=booking.id,
                price_id=price_id,
                total_amount=block_amount_cents,
                commission_percentage=commission_rate,
                commission_amount=commission_amount,
                teacher_amount=teacher_amount,
                platform_amount=commission_amount,
                transfer_date=transfer_date,
                transfer_status="pending",
                teacher_stripe_account_id=teacher_stripe_account_id,
                application_fee_amount=commission_amount if commission_amount > 0 else None,
                status_id=active_status.id,
                stripe_payment_intent_id=payment_intent_id,
            )
            db.add(payment_booking)
            await db.flush()

            confirmation = Confirmation(
                teacher_id=teacher_id,
                student_id=user_id,
                payment_booking_id=payment_booking.id,
            )
            db.add(confirmation)
            await db.flush()

            booking_details = {
                'booking_id': booking.id,
                'date': booking.start_time.strftime('%d/%m/%Y %H:%M'),
                'start_date': booking.start_time.strftime('%d/%m/%Y %H:%M'),
                'end_date': booking.end_time.strftime('%d/%m/%Y %H:%M'),
                'student_name': f"{user.first_name} {user.last_name}",
                'teacher_name': teacher_name,
            }
            payment_details = {
                'payment_id': payment_booking.id,
                'amount': payment_booking.total_amount,
            }
            await send_booking_confirmation_to_student(db, user_id, booking_details)
            await send_payment_confirmation_notification(db, user_id, payment_details)
            await send_booking_notification_to_teacher(db, teacher_id, booking_details)
            await send_booking_confirmation_email(db, user_id, booking_details)
            await send_payment_confirmation_email(db, user_id, payment_details)
            await send_new_booking_email_to_teacher(db, teacher_id, booking_details)

            created_booking_ids.append(booking.id)
            created_payment_ids.append(payment_booking.id)
            created_confirmation_ids.append(confirmation.id)

        await db.commit()
        return {
            "bookings": created_booking_ids,
            "payment_bookings": created_payment_ids,
            "confirmations": created_confirmation_ids,
            "payment_status": session.payment_status,
        }

    # Convierte los strings a datetime (modo single)
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

    # Obtener datos del usuario (estudiante)
    user_result = await db.execute(select(User).where(User.id == user_id))
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
