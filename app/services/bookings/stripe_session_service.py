from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from datetime import datetime

from app.models.teachers.availability import Availability
from app.models.teachers.price import Price
from app.models.users.user import User
from app.external.stripe_config import stripe
from app.services.bookings.commission_service import get_teacher_commission_rate, get_teacher_wallet, calculate_commission_amounts

async def create_booking_payment_session(db: AsyncSession, user: User, booking_data):
    # 1. Validar que la disponibilidad existe y cargar la relación user
    disponibilidad_result = await db.execute(
        select(Availability)
        .options(joinedload(Availability.user))
        .where(Availability.id == booking_data.availability_id)
    )
    disponibilidad = disponibilidad_result.scalar_one_or_none()

    if not disponibilidad:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    # 2. Convertir fechas para validaciones
    if isinstance(booking_data.start_time, str):
        requested_start = datetime.fromisoformat(booking_data.start_time)
    else:
        requested_start = booking_data.start_time
        
    if isinstance(booking_data.end_time, str):
        requested_end = datetime.fromisoformat(booking_data.end_time)
    else:
        requested_end = booking_data.end_time

    # 3. Validar que no se puede reservar en fechas pasadas
    current_time = datetime.now()
    if requested_start <= current_time:
        raise HTTPException(
            status_code=400,
            detail="No se puede reservar una clase en una fecha y hora que ya pasó"
        )
    
    if requested_end <= current_time:
        raise HTTPException(
            status_code=400,
            detail="La hora de fin de la clase no puede ser en el pasado"
        )

    # 4. Validar que el horario solicitado está dentro del rango del docente
    if not (disponibilidad.start_time <= requested_start < requested_end <= disponibilidad.end_time):
        raise HTTPException(
            status_code=400,
            detail="El horario solicitado no está dentro del rango de disponibilidad del docente"
        )

    # 5. Validar que no hay traslape con otra reserva ya existente en esa disponibilidad
    from app.models.booking.bookings import Booking
    from app.models.common.status import Status
    
    # Obtener el ID del status 'cancelled'
    cancelled_status_result = await db.execute(select(Status).where(Status.name == "cancelled"))
    cancelled_status = cancelled_status_result.scalar_one_or_none()
    cancelled_status_id = cancelled_status.id if cancelled_status else None
    
    overlap_result = await db.execute(
        select(Booking).where(
            Booking.availability_id == booking_data.availability_id,
            Booking.start_time < requested_end,
            Booking.end_time > requested_start,
            Booking.status_id != cancelled_status_id if cancelled_status_id else True
        )
    )
    existing_booking = overlap_result.scalar_one_or_none()
    if existing_booking:
        # Formatear las fechas para mostrar en el error
        existing_start = existing_booking.start_time.strftime('%d/%m/%Y %H:%M')
        existing_end = existing_booking.end_time.strftime('%d/%m/%Y %H:%M')
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una reserva en ese horario: {existing_start} - {existing_end}. Por favor selecciona otro horario."
        )

    # 6. Validar que el MISMO USUARIO no tenga otra reserva al mismo tiempo
    user_overlap_result = await db.execute(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.start_time < requested_end,
            Booking.end_time > requested_start,
            Booking.status_id != cancelled_status_id if cancelled_status_id else True
        )
    )
    user_existing_booking = user_overlap_result.scalar_one_or_none()
    if user_existing_booking:
        # Formatear las fechas para mostrar en el error
        user_existing_start = user_existing_booking.start_time.strftime('%d/%m/%Y %H:%M')
        user_existing_end = user_existing_booking.end_time.strftime('%d/%m/%Y %H:%M')
        raise HTTPException(
            status_code=400,
            detail=f"Ya tienes una reserva en ese horario: {user_existing_start} - {user_existing_end}. No puedes reservar dos clases al mismo tiempo."
        )

    # 7. Validar que la reserva tiene al menos 1 hora de anticipación
    time_difference = (requested_start - current_time).total_seconds() / 3600  # en horas
    if time_difference < 1:
        raise HTTPException(
            status_code=400,
            detail="Debes reservar la clase con al menos 1 hora de anticipación"
        )

    # 8. Obtener el precio asociado al docente y preferencia
    price_result = await db.execute(
        select(Price).where(
            Price.user_id == disponibilidad.user_id,
            Price.preference_id == disponibilidad.preference_id
        )
    )
    price = price_result.scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")

    # 6. Obtener información del docente para comisiones
    teacher_id = disponibilidad.user_id
    print(f"🎯 DEBUG: Teacher ID: {teacher_id}")
    
    commission_rate = await get_teacher_commission_rate(db, teacher_id)
    print(f"📊 DEBUG: Commission rate obtenida: {commission_rate}%")
    
    teacher_wallet = await get_teacher_wallet(db, teacher_id)
    print(f"💳 DEBUG: Teacher wallet: {teacher_wallet.stripe_account_id}")

    # 7. Calcular el precio total basado en las horas
    if isinstance(booking_data.start_time, str):
        start_time = datetime.fromisoformat(booking_data.start_time)
    else:
        start_time = booking_data.start_time
        
    if isinstance(booking_data.end_time, str):
        end_time = datetime.fromisoformat(booking_data.end_time)
    else:
        end_time = booking_data.end_time
        
    total_hours = (end_time - start_time).total_seconds() / 3600

    if total_hours <= 0:
        raise HTTPException(status_code=400, detail="Las horas deben ser positivas")

    # Calcular precio: primera hora + horas adicionales
    total_price = price.selected_prices + (total_hours - 1) * price.extra_hour_price
    total_amount_cents = int(total_price * 100)  # Convertir a centavos
    print(f"💵 DEBUG: Total price: ${total_price} MXN = {total_amount_cents} centavos")
    
    # Calcular comisiones
    commission_amount, teacher_amount = calculate_commission_amounts(total_amount_cents, commission_rate)
    
    # 8. Crear sesión de pago en Stripe con Stripe Connect
    session_data = {
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price_data": {
                    "currency": "mxn",
                    "product_data": {
                        "name": f"Clase con {disponibilidad.user.first_name} {disponibilidad.user.last_name}",
                        "description": f"Clase de {total_hours} hora(s) - {start_time.strftime('%d/%m/%Y %H:%M')} a {end_time.strftime('%d/%m/%Y %H:%M')}",
                    },
                    "unit_amount": total_amount_cents,
                },
                "quantity": 1,
            }
        ],
        "mode": "payment",
        "success_url": "http://localhost:5173/?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "http://localhost:5173/",
        "customer_email": user.email,  # Email del estudiante pre-llenado automáticamente
        "metadata": {
            "user_id": str(user.id),
            "price_id": str(price.id),
            "availability_id": str(booking_data.availability_id),
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "total_hours": str(total_hours),
            "teacher_id": str(teacher_id),
            "teacher_email": disponibilidad.user.email,  # Email del docente
            "commission_rate": str(commission_rate),
            "commission_amount": str(commission_amount),
            "teacher_amount": str(teacher_amount),
            "teacher_stripe_account_id": teacher_wallet.stripe_account_id
        }
    }
    
    # Si hay comisión, usar Stripe Connect para dividir el pago
    print(f"🔧 DEBUG: Configurando Stripe Connect...")
    if commission_amount > 0:
        print(f"💰 DEBUG: Aplicando comisión de {commission_amount} centavos a la plataforma")
        session_data["payment_intent_data"] = {
            "application_fee_amount": commission_amount,
            "transfer_data": {
                "destination": teacher_wallet.stripe_account_id,
                # No especificar amount - Stripe automáticamente transfiere el resto
            },
        }
        print(f"✅ DEBUG: Stripe Connect configurado CON comisión:")
        print(f"   - application_fee_amount: {commission_amount}")
        print(f"   - destination: {teacher_wallet.stripe_account_id}")
    else:
        print(f"⭐ DEBUG: Sin comisión - transfiriendo todo al docente")
        # Si no hay comisión (plan premium), transferir todo al docente
        session_data["payment_intent_data"] = {
            "transfer_data": {
                "destination": teacher_wallet.stripe_account_id,
                # No especificar amount - Stripe transfiere el total
            },
        }
        print(f"✅ DEBUG: Stripe Connect configurado SIN comisión:")
        print(f"   - destination: {teacher_wallet.stripe_account_id}")
        print(f"   - sin application_fee_amount")
    
    session = stripe.checkout.Session.create(**session_data)
    return {
        "url": session.url,
        "session_id": session.id,
        "price": price.selected_prices + (total_hours - 1) * price.extra_hour_price
    }
