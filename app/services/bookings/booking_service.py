from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.teachers.price import Price
from app.models.users.user import User
from app.models.common.status import Status
from app.models.subscriptions.subscription import Subscription
from app.models.subscriptions.plan import Plan
from app.models.teachers.wallet import Wallet
from app.external.stripe_config import stripe
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.teachers.availability import Availability
from app.services.notifications.notification_service import create_booking_payment_notification, create_teacher_booking_notification
import hashlib
import secrets

async def get_active_status(db: AsyncSession):
    result = await db.execute(select(Status).where(Status.name == "active"))
    return result.scalar_one_or_none()

async def get_teacher_commission_rate(db: AsyncSession, teacher_id: int):
    """Obtiene el porcentaje de comisión según el plan del docente"""
    print(f"🔍 DEBUG: Buscando comisión para teacher_id: {teacher_id}")
    
    # Buscar suscripción activa del docente con join explícito
    subscription_result = await db.execute(
        select(Subscription, Plan)
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(Status, Subscription.status_id == Status.id)
        .where(
            Subscription.user_id == teacher_id,
            Status.name == "active"
        )
        .order_by(Subscription.start_date.desc())
    )
    result = subscription_result.first()
    
    if not result:
        # Si no tiene suscripción, usar plan gratuito por defecto
        print(f"⚠️ DEBUG: No se encontró suscripción activa para teacher_id {teacher_id}, usando plan gratuito (60%)")
        return 60.00
    
    subscription, plan = result
    print(f"📋 DEBUG: Suscripción encontrada - Plan: {plan.name}, ID: {plan.id}")
    
    # Plan gratuito = 60% comisión, Plan premium = 0% comisión
    if plan.name == "Plan Gratuito":
        print(f"💰 DEBUG: Plan Gratuito detectado - Comisión: 60%")
        return 60.00
    elif plan.name == "Plan Premium":
        print(f"⭐ DEBUG: Plan Premium detectado - Comisión: 0%")
        return 0.00
    else:
        print(f"❓ DEBUG: Plan desconocido '{plan.name}' - Usando comisión por defecto: 60%")
        return 60.00  # Por defecto

async def get_teacher_wallet(db: AsyncSession, teacher_id: int):
    """Obtiene la cartera Stripe del docente"""
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == teacher_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    
    if not wallet or not wallet.stripe_account_id:
        raise HTTPException(
            status_code=400, 
            detail="El docente no tiene configurada su cuenta de Stripe Connect"
        )
    
    if wallet.stripe_bank_status != "active":
        raise HTTPException(
            status_code=400,
            detail="La cuenta Stripe del docente no está activa"
        )
    
    return wallet

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

    # 3. Validar que el horario solicitado está dentro del rango del docente
    if not (disponibilidad.start_time <= requested_start < requested_end <= disponibilidad.end_time):
        raise HTTPException(
            status_code=400,
            detail="El horario solicitado no está dentro del rango de disponibilidad del docente"
        )

    # 4. Validar que no hay traslape con otra reserva ya existente
    overlap_result = await db.execute(
        select(Booking).where(
            Booking.availability_id == booking_data.availability_id,
            Booking.start_time < requested_end,
            Booking.end_time > requested_start
        )
    )
    if overlap_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ya existe una reserva para ese horario"
        )

    # 2. Obtener el precio asociado al docente y preferencia
    price_result = await db.execute(
        select(Price).where(
            Price.user_id == disponibilidad.user_id,
            Price.preference_id == disponibilidad.preference_id
        )
    )
    price = price_result.scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Precio no encontrado para este docente")

    # 3. Obtener información del docente para comisiones
    teacher_id = disponibilidad.user_id
    print(f"🎯 DEBUG: Teacher ID: {teacher_id}")
    
    commission_rate = await get_teacher_commission_rate(db, teacher_id)
    print(f"📊 DEBUG: Commission rate obtenida: {commission_rate}%")
    
    teacher_wallet = await get_teacher_wallet(db, teacher_id)
    print(f"💳 DEBUG: Teacher wallet: {teacher_wallet.stripe_account_id}")

    # 4. Calcular el precio total basado en las horas
    # Convertir a datetime si es string, o usar directamente si ya es datetime
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
    commission_amount = int(total_amount_cents * (commission_rate / 100))
    teacher_amount = total_amount_cents - commission_amount
    print(f"🧮 DEBUG: Commission calculation:")
    print(f"   - Total: {total_amount_cents} centavos")
    print(f"   - Commission rate: {commission_rate}%")
    print(f"   - Commission amount: {commission_amount} centavos")
    print(f"   - Teacher amount: {teacher_amount} centavos")
    
    # 5. Crear sesión de pago en Stripe con Stripe Connect
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
        "metadata": {
            "user_id": str(user.id),
            "price_id": str(price.id),
            "availability_id": str(booking_data.availability_id),
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "total_hours": str(total_hours),
            "teacher_id": str(teacher_id),
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
    # Obtener información del docente para el room name
    teacher_id = booking.availability.user_id if hasattr(booking, 'availability') else int(session.metadata["teacher_id"])
    
    # Crear un hash único basado en booking_id, teacher_id, user_id y timestamp
    unique_data = f"{booking.id}-{teacher_id}-{user_id}-{int(start_time.timestamp())}"
    room_hash = hashlib.md5(unique_data.encode()).hexdigest()[:8]
    
    # Generar token adicional para mayor seguridad
    security_token = secrets.token_hex(4)
    
    # Crear room name más seguro: teacher_id-student_id-hash-token
    room_name = f"onlycation-{teacher_id}x{user_id}-{room_hash}-{security_token}"
    class_link = f"https://meet.jit.si/{room_name}"
    booking.class_space = class_link
    
    print(f"🔗 DEBUG: Room creado: {room_name}")
    print(f"🔗 DEBUG: Link de clase: {class_link}")

    


    # Recarga el booking con la relación availability
    booking_result = await db.execute(
        select(Booking).options(joinedload(Booking.availability)).where(Booking.id == booking.id)
    )
    booking = booking_result.scalar_one()

    # Obtener datos de comisión desde metadata
    commission_rate = float(session.metadata.get("commission_rate", "5.00"))
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