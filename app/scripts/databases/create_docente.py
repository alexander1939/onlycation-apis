from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.users.user import User
from app.models.users.profile import Profile
from app.models.users.preference import Preference
from app.models.teachers.price import Price
from app.models.teachers.availability import Availability
from app.models.teachers.wallet import Wallet
from app.models.teachers.document import Document
from app.models.teachers.video import Video
from app.models.booking.bookings import Booking
from app.models.booking.payment_bookings import PaymentBooking
from app.models.booking.confirmation import Confirmation
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.subscriptions.subscription import Subscription
from sqlalchemy import select
from datetime import datetime, timedelta, time
from app.models.common.stripe_price import StripePrice
from app.external.stripe_config import stripe_config
import stripe
from app.cores.security import get_password_hash
from app.models.common.status import Status


async def crear_docente():
    async with async_session() as db:
        # Validar si ya existe el usuario por email
        result = await db.execute(
            select(User).where(User.email == "docente_prueba@example.com")
        )
        docente = result.scalar_one_or_none()
        if not docente:
            docente = User(
                first_name="Juan",
                last_name="Pérez",
                email="docente_prueba@example.com",
                password=get_password_hash("12345678"),  # Contraseña de prueba hasheada
                role_id=1,  # Asume que 1 es el rol de docente
                status_id=1  # Asume que 1 es status activo
            )
            db.add(docente)
            await db.flush()  # Para obtener el id
            print("Usuario creado.")
        else:
            print("El docente ya existe.")

        # Validar perfil
        perfil_result = await db.execute(
            select(Profile).where(Profile.user_id == docente.id)
        )
        perfil = perfil_result.scalar_one_or_none()
        if not perfil:
            perfil = Profile(
                user_id=docente.id,
                credential="Licenciado en Matemáticas",
                gender="Masculino",
                sex="M"
            )
            db.add(perfil)
            print("Perfil creado.")
        else:
            print("El perfil ya existe.")

        # Validar preferencia
        preferencia_result = await db.execute(
            select(Preference).where(Preference.user_id == docente.id)
        )
        preferencia = preferencia_result.scalar_one_or_none()
        if not preferencia:
            preferencia = Preference(
                user_id=docente.id,
                educational_level_id=1,  # Asume que existe
                modality_id=1,           # Asume que existe
                location="CDMX",
                location_description="Zona centro"
            )
            db.add(preferencia)
            await db.flush()
            print("Preferencia creada.")
        else:
            print("La preferencia ya existe.")

        # Precio principal
        selected_price = 250.0
        tipo = "tutorias"
        currency = "mxn"

        # Validar precio principal en StripePrice
        stripe_price_result = await db.execute(
            select(StripePrice).where(
                StripePrice.amount == selected_price,
                StripePrice.type == tipo
            )
        )
        stripe_price_entry = stripe_price_result.scalar_one_or_none()

        if not stripe_price_entry:
            product = stripe.Product.create(
                name=f"Tutoría precio {selected_price}",
                description="Pago por tutoría individual"
            )
            price = stripe.Price.create(
                unit_amount=int(selected_price * 100),
                currency=currency,
                product=product.id
            )
            stripe_price_entry = StripePrice(
                stripe_product_id=product.id,
                stripe_price_id=price.id,
                amount=selected_price,
                currency=currency,
                type=tipo
            )
            db.add(stripe_price_entry)
            await db.flush()
            print("StripePrice principal creado y guardado en BD.")
        else:
            print("Ya existe un StripePrice principal para ese monto y tipo.")

        # Precio extra hora (la mitad)
        extra_hour_price = selected_price / 2

        stripe_extra_result = await db.execute(
            select(StripePrice).where(
                StripePrice.amount == extra_hour_price,
                StripePrice.type == tipo
            )
        )
        stripe_extra_entry = stripe_extra_result.scalar_one_or_none()

        if not stripe_extra_entry:
            product_extra = stripe.Product.create(
                name=f"Tutoría precio {extra_hour_price}",
                description="Pago por hora extra de tutoría"
            )
            price_extra = stripe.Price.create(
                unit_amount=int(extra_hour_price * 100),
                currency=currency,
                product=product_extra.id
            )
            stripe_extra_entry = StripePrice(
                stripe_product_id=product_extra.id,
                stripe_price_id=price_extra.id,
                amount=extra_hour_price,
                currency=currency,
                type=tipo
            )
            db.add(stripe_extra_entry)
            await db.flush()
            print("StripePrice extra hora creado y guardado en BD.")
        else:
            print("Ya existe un StripePrice para el precio extra hora.")

        # Crear registro de precio del docente usando ambos StripePrice
        precio_result = await db.execute(
            select(Price).where(Price.user_id == docente.id)
        )
        precio = precio_result.scalar_one_or_none()
        if not precio:
            precio = Price(
                user_id=docente.id,
                preference_id=preferencia.id,
                price_range_id=1,
                selected_prices=selected_price,
                extra_hour_price=extra_hour_price,
                stripe_product_id=stripe_price_entry.stripe_product_id,
                stripe_price_id=stripe_price_entry.stripe_price_id,
                stripe_extra_product_id=stripe_extra_entry.stripe_product_id,
                stripe_extra_price_id=stripe_extra_entry.stripe_price_id
            )
            db.add(precio)
            print("Precio creado y vinculado a StripePrice y StripePrice extra.")
        else:
            print("El precio ya existe.")

        # La disponibilidad se puede repetir cada vez
        # Validar disponibilidad
        disponibilidad_result = await db.execute(
            select(Availability).where(Availability.user_id == docente.id)
        )
        disponibilidades = disponibilidad_result.scalars().all()
        if not disponibilidades:
            manana = datetime.today() + timedelta(days=1)

            disponibilidad = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=1,  # Lunes
                start_time=datetime.combine(datetime.today(), time(hour=9, minute=0)),   # 09:00
                end_time=datetime.combine(datetime.today(), time(hour=22, minute=0))    # 22:00
            )
            disponibilidad2 = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=1,  # Lunes
                start_time=datetime.combine(manana.date(), time(hour=9, minute=0)),   # 09:00 mañana
                end_time=datetime.combine(manana.date(), time(hour=22, minute=0))     # 22:00 mañana
            )
            db.add(disponibilidad)
            db.add(disponibilidad2)
            print("Disponibilidad creada.")
        else:
            print("La disponibilidad ya existe.")

        # Crear wallet con cuenta Stripe activa
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == docente.id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(
                user_id=docente.id,
                stripe_account_id="acct_1RzrVLRvLAM1ndJe",  # Cuenta Stripe activa de prueba
                stripe_bank_status="active",  # Estado activo para pruebas
                stripe_setup_url=None  # No necesita setup URL porque ya está activo
            )
            db.add(wallet)
            print("Wallet creado con cuenta Stripe activa.")
        else:
            print("El wallet ya existe.")

        # Asignar plan gratuito por defecto
        subscription_result = await db.execute(
            select(Subscription).where(Subscription.user_id == docente.id).limit(1)
        )
        existing_subscription = subscription_result.scalar_one_or_none()
        if not existing_subscription:
            # Buscar el plan gratuito
            free_plan_result = await db.execute(
                select(Plan).where(Plan.name == "Plan Gratuito")
            )
            free_plan = free_plan_result.scalar_one_or_none()
            
            if free_plan:
                # Crear PaymentSubscription (validación del pago)
                payment_subscription = PaymentSubscription(
                    user_id=docente.id,
                    plan_id=free_plan.id,
                    status_id=1,  # Asume que 1 es status activo
                    stripe_payment_intent_id=None  # No hay Stripe para plan gratuito
                )
                db.add(payment_subscription)
                await db.flush()
                
                # Crear Subscription (validación de fechas y estado)
                subscription = Subscription(
                    user_id=docente.id,
                    plan_id=free_plan.id,
                    payment_suscription_id=payment_subscription.id,
                    start_date=datetime.utcnow(),
                    end_date=None,  # Plan gratuito ilimitado
                    status_id=1  # Activo
                )
                db.add(subscription)
                print("Plan gratuito asignado al docente de prueba.")
            else:
                print("Plan gratuito no encontrado. Ejecuta create_plan.py primero.")
        else:
            print("El docente ya tiene una suscripción.")

        # =====================
        # Documento del docente
        # =====================
        doc_res = await db.execute(select(Document).where(Document.user_id == docente.id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            # Valores dummy seguros para pruebas (no reales)
            doc = Document(
                user_id=docente.id,
                rfc_hash="dummy_hash_pruebas_123",
                rfc_cipher="dummy_cipher_base64",
                certificate="/evidence/certs/dummy.enc",
                curriculum="/evidence/cv/dummy.enc",
                expertise_area="Matemáticas",
                description="Docente de matemáticas con experiencia en álgebra y cálculo"
            )
            db.add(doc)
            print("Documento del docente creado.")
        else:
            print("El documento del docente ya existe.")

        # =====================
        # Video del docente
        # =====================
        video_res = await db.execute(select(Video).where(Video.user_id == docente.id))
        video = video_res.scalar_one_or_none()
        if not video:
            video = Video(
                user_id=docente.id,
                youtube_video_id="dQw4w9WgXcQ",
                title="Presentación docente",
                thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                duration_seconds=180,
                embed_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
                privacy_status="public",
                embeddable=True,
                original_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )
            db.add(video)
            print("Video del docente creado.")
        else:
            print("El video del docente ya existe.")

        # =====================
        # Crear alumno de prueba
        # =====================
        student_res = await db.execute(select(User).where(User.email == "alumno_prueba@example.com"))
        alumno = student_res.scalar_one_or_none()
        if not alumno:
            alumno = User(
                first_name="Luis",
                last_name="García",
                email="alumno_prueba@example.com",
                password=get_password_hash("12345678"),
                role_id=2,  # asumiendo 2 = alumno
                status_id=1,
            )
            db.add(alumno)
            await db.flush()
            # perfil simple opcional
            perfil_alumno = Profile(
                user_id=alumno.id,
                credential="Estudiante",
                gender="Masculino",
                sex="M",
            )
            db.add(perfil_alumno)
            print("Alumno de prueba creado.")
        else:
            print("El alumno de prueba ya existe.")

        # =====================
        # Crear una reserva futura (Booking) entre alumno y docente
        # =====================
        # Tomar o crear una disponibilidad futura válida
        disponibilidad_futura = None
        disp_q = await db.execute(select(Availability).where(Availability.user_id == docente.id))
        disponibilidades = disp_q.scalars().all()
        if disponibilidades:
            disponibilidad_futura = disponibilidades[0]
        else:
            # en caso extremo crear una disponibilidad para mañana
            manana = datetime.today() + timedelta(days=1)
            disponibilidad_futura = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=manana.weekday(),
                start_time=datetime.combine(manana.date(), time(hour=9, minute=0)),
                end_time=datetime.combine(manana.date(), time(hour=22, minute=0)),
            )
            db.add(disponibilidad_futura)
            await db.flush()

        # Definir un horario dentro de la disponibilidad
        clase_inicio = max(disponibilidad_futura.start_time, datetime.utcnow() + timedelta(days=1, hours=1))
        clase_fin = clase_inicio + timedelta(hours=1)

        # Verificar si ya existe un booking idéntico
        booking_q = await db.execute(
            select(Booking).where(
                Booking.user_id == alumno.id,
                Booking.availability_id == disponibilidad_futura.id,
                Booking.start_time == clase_inicio,
                Booking.end_time == clase_fin,
            )
        )
        booking = booking_q.scalar_one_or_none()
        if not booking:
            # status para booking (usar "approved" si existe)
            status_approved = (await db.execute(select(Status).where(Status.name == "approved"))).scalar_one_or_none()
            booking = Booking(
                user_id=alumno.id,
                availability_id=disponibilidad_futura.id,
                start_time=clase_inicio,
                end_time=clase_fin,
                status_id=status_approved.id if status_approved else None,
                class_space="zoom"
            )
            db.add(booking)
            await db.flush()
            print("Booking de prueba creado.")
        else:
            print("El booking de prueba ya existe.")

        # =====================
        # PaymentBooking asociado
        # =====================
        pay_q = await db.execute(select(PaymentBooking).where(PaymentBooking.booking_id == booking.id))
        pay = pay_q.scalar_one_or_none()
        if not pay:
            total_amount = int(precio.selected_prices * 100)
            pay = PaymentBooking(
                user_id=alumno.id,
                booking_id=booking.id,
                price_id=precio.id,
                total_amount=total_amount,
                commission_percentage=0,
                commission_amount=0,
                teacher_amount=total_amount,
                platform_amount=0,
                status_id=status_approved.id if status_approved else None,
                stripe_payment_intent_id="pi_dummy_test",
            )
            db.add(pay)
            await db.flush()
            print("PaymentBooking de prueba creado.")
        else:
            print("El PaymentBooking de prueba ya existe.")

        # =====================
        # Confirmation de la clase
        # =====================
        conf_q = await db.execute(select(Confirmation).where(Confirmation.payment_booking_id == pay.id))
        conf = conf_q.scalar_one_or_none()
        if not conf:
            conf = Confirmation(
                teacher_id=docente.id,
                student_id=alumno.id,
                payment_booking_id=pay.id,
                confirmation_date_teacher=False,
                confirmation_date_student=False,
                description_teacher="Clase programada",
                description_student="Listo para la clase",
            )
            db.add(conf)
            print("Confirmation de prueba creada.")
        else:
            print("La Confirmation de prueba ya existe.")

        await db.commit()
        print("Docente de prueba creado con documentos, video, alumno, booking, payment_booking y confirmation.")
