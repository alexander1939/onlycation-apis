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
from app.models.booking.assessment import Assessment
from app.models.subscriptions.plan import Plan
from app.models.subscriptions.payment_subscription import PaymentSubscription
from app.models.subscriptions.subscription import Subscription
from sqlalchemy import select
from datetime import datetime, timedelta, time
from app.models.common.stripe_price import StripePrice
from app.external.stripe_config import stripe_config
import stripe
from app.cores.security import get_password_hash, rfc_hash_plain, encrypt_text, encrypt_bytes
from app.models.common.status import Status
import os


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
                status_id=1  # Activo
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
            # Crear disponibilidades de hora en hora - SOLO HORAS como STRING
            
            # Crear slots de 9 AM a 10 PM para Lunes (9-10, 10-11, ..., 21-22)
            for hora in range(9, 22):  # 9 a 21 (el último slot será 21:00-22:00)
                disponibilidad = Availability(
                    user_id=docente.id,
                    preference_id=preferencia.id,
                    day_of_week=1,  # Lunes
                    start_time=f"{hora:02d}:00:00",  # String: "09:00:00", "10:00:00", etc.
                    end_time=f"{hora+1:02d}:00:00"   # String: "10:00:00", "11:00:00", etc.
                )
                db.add(disponibilidad)
            
            print("Disponibilidades creadas como strings: 09:00:00, 10:00:00, ..., 22:00:00")
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
                youtube_video_id="kKh2c_YZKDI",
                title="Presentación Juan Pérez - Docente de Matemáticas",
                thumbnail_url=" ",
                duration_seconds=43,
                embed_url="https://www.youtube.com/embed/kKh2c_YZKDI",
                privacy_status="public",
                embeddable=True,
                original_url="https://www.youtube.com/watch?v=kKh2c_YZKDI",
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

        # Obtener status_approved para los bookings
        status_approved = (await db.execute(select(Status).where(Status.name == "approved"))).scalar_one_or_none()

        # =============================================
        # CREAR 4 DOCENTES ADICIONALES CON VIDEOS REALES
        # =============================================
        
        # DOCENTE 2: María López - Física
        result2 = await db.execute(select(User).where(User.email == "maria.lopez@example.com"))
        docente2 = result2.scalar_one_or_none()
        if not docente2:
            docente2 = User(
                first_name="María",
                last_name="López",
                email="maria.lopez@example.com",
                password=get_password_hash("12345678"),
                role_id=1,
                status_id=1
            )
            db.add(docente2)
            await db.flush()
            
            db.add(Profile(user_id=docente2.id, credential="Maestra en Física", gender="Femenino", sex="F"))
            db.add(Preference(user_id=docente2.id, educational_level_id=2, modality_id=1, location="Guadalajara"))
            await db.flush()
            
            pref2_q = await db.execute(select(Preference).where(Preference.user_id == docente2.id))
            pref2 = pref2_q.scalar_one()
            
            db.add(Price(user_id=docente2.id, preference_id=pref2.id, price_range_id=2, selected_prices=300.0, extra_hour_price=150.0))
            db.add(Document(user_id=docente2.id, rfc_hash="hash2", rfc_cipher="cipher2", certificate="/evidence/cert2.enc", curriculum="/evidence/cv2.enc", expertise_area="Física Cuántica", description="Docente de física con especialización en mecánica cuántica"))
            db.add(Video(user_id=docente2.id, youtube_video_id="Unzc731iCUY", title="Presentación María López - Física", thumbnail_url=None, duration_seconds=60, embed_url="https://www.youtube.com/embed/Unzc731iCUY", privacy_status="public", embeddable=True, original_url="https://www.youtube.com/watch?v=Unzc731iCUY"))
            
            # Crear booking y assessment para María
            avail2 = Availability(user_id=docente2.id, preference_id=pref2.id, day_of_week=3, start_time="10:00:00", end_time="11:00:00")
            db.add(avail2)
            await db.flush()
            
            booking2 = Booking(user_id=alumno.id, availability_id=avail2.id, start_time=datetime(2025, 11, 5, 10, 0), end_time=datetime(2025, 11, 5, 11, 0), status_id=status_approved.id if status_approved else None, class_space="zoom")
            db.add(booking2)
            await db.flush()
            
            # Obtener price_id para María
            price2_q = await db.execute(select(Price).where(Price.user_id == docente2.id))
            price2 = price2_q.scalar_one()
            
            pay2 = PaymentBooking(user_id=alumno.id, booking_id=booking2.id, price_id=price2.id, total_amount=30000, commission_percentage=0, commission_amount=0, teacher_amount=30000, platform_amount=0, status_id=status_approved.id if status_approved else None, stripe_payment_intent_id="pi_test2")
            db.add(pay2)
            await db.flush()
            
            assess2 = Assessment(user_id=alumno.id, payment_booking_id=pay2.id, qualification=4, comment="Muy buena clase de física, explicaciones claras.")
            db.add(assess2)
            
            print("✅ Docente 2 (María López - Física) creado con assessment")
        
        # DOCENTE 3: Carlos Ramírez - Química
        result3 = await db.execute(select(User).where(User.email == "carlos.ramirez@example.com"))
        docente3 = result3.scalar_one_or_none()
        if not docente3:
            docente3 = User(
                first_name="Carlos",
                last_name="Ramírez",
                email="carlos.ramirez@example.com",
                password=get_password_hash("12345678"),
                role_id=1,
                status_id=1
            )
            db.add(docente3)
            await db.flush()
            
            db.add(Profile(user_id=docente3.id, credential="Doctor en Química", gender="Masculino", sex="M"))
            db.add(Preference(user_id=docente3.id, educational_level_id=3, modality_id=1, location="Monterrey"))
            await db.flush()
            
            pref3_q = await db.execute(select(Preference).where(Preference.user_id == docente3.id))
            pref3 = pref3_q.scalar_one()
            
            db.add(Price(user_id=docente3.id, preference_id=pref3.id, price_range_id=3, selected_prices=350.0, extra_hour_price=175.0))
            db.add(Document(user_id=docente3.id, rfc_hash="hash3", rfc_cipher="cipher3", certificate="/evidence/cert3.enc", curriculum="/evidence/cv3.enc", expertise_area="Química Orgánica", description="Profesor de química especializado en síntesis orgánica"))
            db.add(Video(user_id=docente3.id, youtube_video_id="mOJ0XspgRxE", title="Presentación Carlos Ramírez - Química", thumbnail_url=None, duration_seconds=55, embed_url="https://www.youtube.com/embed/mOJ0XspgRxE", privacy_status="public", embeddable=True, original_url="https://www.youtube.com/watch?v=mOJ0XspgRxE"))
            
            # Crear booking y assessment para Carlos
            avail3 = Availability(user_id=docente3.id, preference_id=pref3.id, day_of_week=4, start_time="14:00:00", end_time="15:00:00")
            db.add(avail3)
            await db.flush()
            
            booking3 = Booking(user_id=alumno.id, availability_id=avail3.id, start_time=datetime(2025, 11, 6, 14, 0), end_time=datetime(2025, 11, 6, 15, 0), status_id=status_approved.id if status_approved else None, class_space="zoom")
            db.add(booking3)
            await db.flush()
            
            # Obtener price_id para Carlos
            price3_q = await db.execute(select(Price).where(Price.user_id == docente3.id))
            price3 = price3_q.scalar_one()
            
            pay3 = PaymentBooking(user_id=alumno.id, booking_id=booking3.id, price_id=price3.id, total_amount=35000, commission_percentage=0, commission_amount=0, teacher_amount=35000, platform_amount=0, status_id=status_approved.id if status_approved else None, stripe_payment_intent_id="pi_test3")
            db.add(pay3)
            await db.flush()
            
            assess3 = Assessment(user_id=alumno.id, payment_booking_id=pay3.id, qualification=5, comment="Excelente profesor de química, muy recomendado.")
            db.add(assess3)
            
            print("✅ Docente 3 (Carlos Ramírez - Química) creado con assessment")
        
        # DOCENTE 4: Ana Martínez - Inglés
        result4 = await db.execute(select(User).where(User.email == "ana.martinez@example.com"))
        docente4 = result4.scalar_one_or_none()
        if not docente4:
            docente4 = User(
                first_name="Ana",
                last_name="Martínez",
                email="ana.martinez@example.com",
                password=get_password_hash("12345678"),
                role_id=1,
                status_id=1
            )
            db.add(docente4)
            await db.flush()
            
            db.add(Profile(user_id=docente4.id, credential="Licenciada en Lingüística", gender="Femenino", sex="F"))
            db.add(Preference(user_id=docente4.id, educational_level_id=1, modality_id=1, location="CDMX"))
            await db.flush()
            
            pref4_q = await db.execute(select(Preference).where(Preference.user_id == docente4.id))
            pref4 = pref4_q.scalar_one()
            
            db.add(Price(user_id=docente4.id, preference_id=pref4.id, price_range_id=1, selected_prices=200.0, extra_hour_price=100.0))
            db.add(Document(user_id=docente4.id, rfc_hash="hash4", rfc_cipher="cipher4", certificate="/evidence/cert4.enc", curriculum="/evidence/cv4.enc", expertise_area="Inglés Avanzado", description="Maestra de inglés certificada TOEFL con experiencia internacional"))
            db.add(Video(user_id=docente4.id, youtube_video_id="9No-FiEInLA", title="Presentación Ana Martínez - Inglés", thumbnail_url=None, duration_seconds=48, embed_url="https://www.youtube.com/embed/9No-FiEInLA", privacy_status="public", embeddable=True, original_url="https://www.youtube.com/watch?v=9No-FiEInLA"))
            
            # Crear booking y assessment para Ana
            avail4 = Availability(user_id=docente4.id, preference_id=pref4.id, day_of_week=5, start_time="16:00:00", end_time="17:00:00")
            db.add(avail4)
            await db.flush()
            
            booking4 = Booking(user_id=alumno.id, availability_id=avail4.id, start_time=datetime(2025, 11, 7, 16, 0), end_time=datetime(2025, 11, 7, 17, 0), status_id=status_approved.id if status_approved else None, class_space="zoom")
            db.add(booking4)
            await db.flush()
            
            # Obtener price_id para Ana
            price4_q = await db.execute(select(Price).where(Price.user_id == docente4.id))
            price4 = price4_q.scalar_one()
            
            pay4 = PaymentBooking(user_id=alumno.id, booking_id=booking4.id, price_id=price4.id, total_amount=20000, commission_percentage=0, commission_amount=0, teacher_amount=20000, platform_amount=0, status_id=status_approved.id if status_approved else None, stripe_payment_intent_id="pi_test4")
            db.add(pay4)
            await db.flush()
            
            assess4 = Assessment(user_id=alumno.id, payment_booking_id=pay4.id, qualification=4, comment="Buena maestra de inglés, muy paciente.")
            db.add(assess4)
            
            print("✅ Docente 4 (Ana Martínez - Inglés) creado con assessment")
        
        # DOCENTE 5: Roberto Silva - Programación
        result5 = await db.execute(select(User).where(User.email == "roberto.silva@example.com"))
        docente5 = result5.scalar_one_or_none()
        if not docente5:
            docente5 = User(
                first_name="Roberto",
                last_name="Silva",
                email="roberto.silva@example.com",
                password=get_password_hash("12345678"),
                role_id=1,
                status_id=1
            )
            db.add(docente5)
            await db.flush()
            
            db.add(Profile(user_id=docente5.id, credential="Ingeniero en Sistemas", gender="Masculino", sex="M"))
            db.add(Preference(user_id=docente5.id, educational_level_id=2, modality_id=1, location="Puebla"))
            await db.flush()
            
            pref5_q = await db.execute(select(Preference).where(Preference.user_id == docente5.id))
            pref5 = pref5_q.scalar_one()
            
            db.add(Price(user_id=docente5.id, preference_id=pref5.id, price_range_id=2, selected_prices=400.0, extra_hour_price=200.0))
            db.add(Document(user_id=docente5.id, rfc_hash="hash5", rfc_cipher="cipher5", certificate="/evidence/cert5.enc", curriculum="/evidence/cv5.enc", expertise_area="Python y JavaScript", description="Desarrollador senior con 10 años de experiencia en desarrollo web"))
            db.add(Video(user_id=docente5.id, youtube_video_id="8T_f5QEFqDg", title="Presentación Roberto Silva - Programación", thumbnail_url=None, duration_seconds=52, embed_url="https://www.youtube.com/embed/8T_f5QEFqDg", privacy_status="public", embeddable=True, original_url="https://www.youtube.com/watch?v=8T_f5QEFqDg"))
            
            # Crear booking y assessment para Roberto
            avail5 = Availability(user_id=docente5.id, preference_id=pref5.id, day_of_week=1, start_time="18:00:00", end_time="19:00:00")
            db.add(avail5)
            await db.flush()
            
            booking5 = Booking(user_id=alumno.id, availability_id=avail5.id, start_time=datetime(2025, 11, 3, 18, 0), end_time=datetime(2025, 11, 3, 19, 0), status_id=status_approved.id if status_approved else None, class_space="zoom")
            db.add(booking5)
            await db.flush()
            
            # Obtener price_id para Roberto
            price5_q = await db.execute(select(Price).where(Price.user_id == docente5.id))
            price5 = price5_q.scalar_one()
            
            pay5 = PaymentBooking(user_id=alumno.id, booking_id=booking5.id, price_id=price5.id, total_amount=40000, commission_percentage=0, commission_amount=0, teacher_amount=40000, platform_amount=0, status_id=status_approved.id if status_approved else None, stripe_payment_intent_id="pi_test5")
            db.add(pay5)
            await db.flush()
            
            assess5 = Assessment(user_id=alumno.id, payment_booking_id=pay5.id, qualification=5, comment="El mejor profesor de programación, explica muy bien.")
            db.add(assess5)
            
            print("✅ Docente 5 (Roberto Silva - Programación) creado con assessment")

        # =====================
        # BOOKING DE PRUEBA
        # =====================
        
        # ELIMINAR DOCUMENTOS ANTIGUOS del docente
        old_docs = await db.execute(
            select(Document).where(Document.user_id == docente.id)
        )
        docs_to_delete = old_docs.scalars().all()
        for old_doc in docs_to_delete:
            # Eliminar archivos físicos si existen
            if old_doc.certificate and os.path.exists(old_doc.certificate):
                os.remove(old_doc.certificate)
            if old_doc.curriculum and os.path.exists(old_doc.curriculum):
                os.remove(old_doc.curriculum)
            await db.delete(old_doc)
        await db.flush()
        print(f"🗑️  Eliminados {len(docs_to_delete)} documentos antiguos")
        
        # ELIMINAR BOOKINGS ANTIGUOS para empezar limpio
        delete_bookings = await db.execute(
            select(Booking).join(Availability).where(Availability.user_id == docente.id)
        )
        old_bookings = delete_bookings.scalars().all()
        
        # Primero eliminar Confirmations y PaymentBookings asociados
        for old_booking in old_bookings:
            payment_booking_q = await db.execute(
                select(PaymentBooking).where(PaymentBooking.booking_id == old_booking.id)
            )
            payment_bookings = payment_booking_q.scalars().all()
            for pb in payment_bookings:
                # Eliminar confirmations de este PaymentBooking
                confirmation_q = await db.execute(
                    select(Confirmation).where(Confirmation.payment_booking_id == pb.id)
                )
                confirmations = confirmation_q.scalars().all()
                for conf in confirmations:
                    await db.delete(conf)
                # Eliminar assessments de este PaymentBooking
                assessment_q = await db.execute(
                    select(Assessment).where(Assessment.payment_booking_id == pb.id)
                )
                assessments = assessment_q.scalars().all()
                for assess in assessments:
                    await db.delete(assess)
                # Luego eliminar el PaymentBooking
                await db.delete(pb)
        
        # Finalmente eliminar los bookings
        for old_booking in old_bookings:
            await db.delete(old_booking)
        await db.flush()
        print(f"🗑️  Eliminados {len(old_bookings)} bookings antiguos")
        
        # ELIMINAR AVAILABILITIES ANTIGUAS
        old_availabilities = await db.execute(
            select(Availability).where(Availability.user_id == docente.id)
        )
        availabilities_to_delete = old_availabilities.scalars().all()
        for old_avail in availabilities_to_delete:
            await db.delete(old_avail)
        await db.flush()
        print(f"🗑️  Eliminadas {len(availabilities_to_delete)} availabilities antiguas")

        # =====================
        # Crear múltiples disponibilidades para Juan
        # =====================
        
        # Crear disponibilidades para diferentes días de la semana
        availability_days = [
            {"day": 1, "name": "Lunes"},    # Monday
            {"day": 2, "name": "Martes"},   # Tuesday  
            {"day": 3, "name": "Miércoles"}, # Wednesday
            {"day": 4, "name": "Jueves"},   # Thursday
            {"day": 5, "name": "Viernes"}   # Friday
        ]
        
        availabilities = []
        for day_info in availability_days:
            disponibilidad = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=day_info["day"],
                start_time="09:00:00",
                end_time="22:00:00"
            )
            db.add(disponibilidad)
            await db.flush()
            availabilities.append(disponibilidad)
            print(f"✅ Availability creada: day_of_week={day_info['day']} ({day_info['name']})")

        # =====================
        # MÚLTIPLES BOOKINGS PARA JUAN PÉREZ (HISTORIAL DE RESERVAS)
        # =====================
        
        # Obtener status_approved para los bookings
        status_approved = (await db.execute(select(Status).where(Status.name == "approved"))).scalar_one_or_none()
        
        # Obtener price_id para Juan
        price_juan_q = await db.execute(select(Price).where(Price.user_id == docente.id))
        price_juan = price_juan_q.scalar_one()
        
        # Lista de bookings históricos para Juan Pérez (fechas que coinciden con disponibilidades)
        bookings_data = [
            {
                "fecha": datetime(2025, 10, 14, 9, 0),  # Martes - Pasado
                "day_of_week": 2,
                "rating": 5,
                "comment": "Excelente clase de matemáticas, muy claro en las explicaciones.",
                "stripe_id": "pi_juan_001"
            },
            {
                "fecha": datetime(2025, 10, 16, 9, 0),  # Jueves - Pasado
                "day_of_week": 4,
                "rating": 5,
                "comment": "Profesor muy paciente, me ayudó mucho con álgebra.",
                "stripe_id": "pi_juan_002"
            },
            {
                "fecha": datetime(2025, 10, 21, 9, 0),  # Martes - Pasado
                "day_of_week": 2,
                "rating": 4,
                "comment": "Buena clase, aunque un poco rápido en algunos temas.",
                "stripe_id": "pi_juan_003"
            },
            {
                "fecha": datetime(2025, 10, 25, 9, 0),   # Viernes - Pasado
                "day_of_week": 5,
                "rating": 5,
                "comment": "Increíble profesor, definitivamente lo recomiendo.",
                "stripe_id": "pi_juan_004"
            },
            {
                "fecha": datetime(2025, 11, 5, 9, 0),  # Martes - Actual
                "day_of_week": 2,
                "rating": 5,
                "comment": "Siempre aprendo algo nuevo en sus clases.",
                "stripe_id": "pi_juan_005"
            },
            {
                "fecha": datetime(2025, 11, 11, 9, 0),  # Martes - Futuro
                "day_of_week": 2,
                "rating": 4,
                "comment": "Muy buen método de enseñanza, clases dinámicas.",
                "stripe_id": "pi_juan_006"
            },
            {
                "fecha": datetime(2025, 11, 25, 9, 0),  # Martes - Futuro
                "day_of_week": 2,
                "rating": 5,
                "comment": "El mejor profesor de matemáticas que he tenido.",
                "stripe_id": "pi_juan_007"
            }
        ]
        
        # Crear múltiples bookings para Juan
        for i, booking_data in enumerate(bookings_data, 1):
            clase_inicio = booking_data["fecha"]
            clase_fin = clase_inicio + timedelta(hours=1)
            
            # Buscar la availability que corresponde al día de la semana
            availability_for_day = None
            for avail in availabilities:
                if avail.day_of_week == booking_data["day_of_week"]:
                    availability_for_day = avail
                    break
            
            if not availability_for_day:
                print(f"❌ No se encontró availability para day_of_week={booking_data['day_of_week']}")
                continue
            
            # Validar que la hora del booking esté dentro del horario de disponibilidad
            booking_time = clase_inicio.time()
            start_time = datetime.strptime(availability_for_day.start_time, "%H:%M:%S").time()
            end_time = datetime.strptime(availability_for_day.end_time, "%H:%M:%S").time()
            
            if not (start_time <= booking_time <= end_time):
                print(f"❌ Booking #{i} fuera de horario: {booking_time} no está entre {start_time}-{end_time}")
                continue
            
            # Crear booking
            booking = Booking(
                user_id=alumno.id,
                availability_id=availability_for_day.id,
                start_time=clase_inicio,
                end_time=clase_fin,
                status_id=status_approved.id if status_approved else None,
                class_space="zoom"
            )
            db.add(booking)
            await db.flush()
            
            # Crear PaymentBooking
            pay = PaymentBooking(
                user_id=alumno.id,
                booking_id=booking.id,
                price_id=price_juan.id,
                total_amount=25000,  # $250 en centavos
                commission_percentage=0,
                commission_amount=0,
                teacher_amount=25000,
                platform_amount=0,
                status_id=status_approved.id if status_approved else None,
                stripe_payment_intent_id=booking_data["stripe_id"]
            )
            db.add(pay)
            await db.flush()
            
            # Crear Confirmation
            conf = Confirmation(
                teacher_id=docente.id,
                student_id=alumno.id,
                payment_booking_id=pay.id,
                confirmation_date_teacher=False,
                confirmation_date_student=False,
                description_teacher=f"Clase de matemáticas #{i}",
                description_student=f"Lista para clase #{i}"
            )
            db.add(conf)
            
            # Crear Assessment (solo para clases pasadas y actuales)
            if clase_inicio <= datetime.now():
                assessment = Assessment(
                    user_id=alumno.id,
                    payment_booking_id=pay.id,
                    qualification=booking_data["rating"],
                    comment=booking_data["comment"]
                )
                db.add(assessment)
            
            day_names = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}
            day_name = day_names.get(booking_data["day_of_week"], "Desconocido")
            print(f"✅ Booking #{i} creado: {clase_inicio.strftime('%Y-%m-%d %H:%M')} ({day_name}) - Rating: {booking_data['rating']}/5 - Horario válido: {booking_time}")
        
        await db.flush()
        print(f"🎉 Juan Pérez ahora tiene {len(bookings_data)} bookings con fechas y horarios que coinciden con sus disponibilidades")
        
        # =====================
        # Documento del docente CON CIFRADO REAL
        # =====================
        from app.cores.security import rfc_hash_plain, encrypt_text, encrypt_bytes
        
        # Crear directorio si no existe
        os.makedirs("uploads/documents", exist_ok=True)
        
        # Leer y cifrar el certificado (3.pdf)
        certificate_source = "3.pdf"
        if os.path.exists(certificate_source):
            with open(certificate_source, "rb") as f:
                cert_data = f.read()
            cert_encrypted = encrypt_bytes(cert_data)
            certificate_path = f"uploads/documents/certificate_{docente.id}.enc"
            with open(certificate_path, "wb") as f:
                f.write(cert_encrypted)
            print(f"✅ Certificado cifrado: {certificate_path}")
        else:
            certificate_path = None
            print(f"⚠️  Archivo {certificate_source} no encontrado")
        
        # Leer y cifrar el currículum (100.pdf)
        curriculum_source = "100.pdf"
        if os.path.exists(curriculum_source):
            with open(curriculum_source, "rb") as f:
                curr_data = f.read()
            curr_encrypted = encrypt_bytes(curr_data)
            curriculum_path = f"uploads/documents/curriculum_{docente.id}.enc"
            with open(curriculum_path, "wb") as f:
                f.write(curr_encrypted)
            print(f"✅ Currículum cifrado: {curriculum_path}")
        else:
            curriculum_path = None
            print(f"⚠️  Archivo {curriculum_source} no encontrado")
        
        # Crear documento solo si ambos archivos existen
        if certificate_path and curriculum_path:
            test_rfc = "DOPE850101ABC"
            doc = Document(
                user_id=docente.id,
                rfc_hash=rfc_hash_plain(test_rfc),
                rfc_cipher=encrypt_text(test_rfc),
                certificate=certificate_path,
                curriculum=curriculum_path,
                expertise_area="Matemáticas Avanzadas",
                description="Docente de matemáticas con experiencia en álgebra y cálculo diferencial e integral"
            )
            db.add(doc)
            await db.flush()
            print("✅ Documento del docente creado con archivos reales cifrados")
        else:
            print("❌ No se pudo crear el documento: faltan archivos PDF")
        
        # Booking FIJO para el 4 de noviembre 2025
        fecha_booking = datetime(2025, 11, 4)  # 4 de noviembre 2025
        
        print(f"📅 BOOKING FIJO: {fecha_booking.strftime('%Y-%m-%d %A')}")
        print(f"📋 AVAILABILITY: day_of_week={2}")

        # Convertir string de hora a datetime para el booking
        hora_inicio = datetime.strptime("09:00:00", "%H:%M:%S").time()
        clase_inicio = datetime.combine(fecha_booking.date(), hora_inicio)
        clase_fin = clase_inicio + timedelta(hours=1)

        # Crear booking nuevo
        booking = Booking(
            user_id=alumno.id,
            availability_id=availabilities[1].id,
            start_time=clase_inicio,
            end_time=clase_fin,
            status_id=status_approved.id if status_approved else None,
            class_space="zoom"
        )
        db.add(booking)
        await db.flush()
        print(f"✅ Booking creado: {clase_inicio} - {clase_fin}")

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

        # =====================
        # Assessment de la clase (Calificación del alumno al docente)
        # =====================
        assessment_q = await db.execute(select(Assessment).where(Assessment.payment_booking_id == pay.id))
        assessment = assessment_q.scalar_one_or_none()
        if not assessment:
            assessment = Assessment(
                user_id=alumno.id,  # El alumno que califica
                payment_booking_id=pay.id,  # Referencia al pago
                qualification=5,  # Calificación de 1-5 estrellas
                comment="Excelente clase, el docente es muy claro y paciente. Totalmente recomendado."
            )
            db.add(assessment)
            print("Assessment de prueba creado.")
        else:
            print("El Assessment de prueba ya existe.")

        await db.commit()
        print("Docente de prueba creado con documentos, video, alumno, booking, payment_booking, confirmation y assessment.")
