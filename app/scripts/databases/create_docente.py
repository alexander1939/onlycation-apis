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
from app.scripts.databases.create_alumno import crear_alumno

# =====================
# Helpers (Docente de prueba)
# =====================
async def _ensure_docente_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == "docente_prueba@example.com"))
    docente = result.scalar_one_or_none()
    if not docente:
        docente = User(
            first_name="Juan",
            last_name="Pérez",
            email="docente_prueba@example.com",
            password=get_password_hash("12345678"),  # Contraseña de prueba hasheada
            role_id=1,  # Docente
            status_id=1  # Activo
        )
        db.add(docente)
        await db.flush()
        print("Usuario creado.")
    else:
        print("El docente ya existe.")
    return docente

async def _ensure_docente_profile(db: AsyncSession, docente: User) -> None:
    perfil_result = await db.execute(select(Profile).where(Profile.user_id == docente.id))
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

async def _ensure_docente_preference(db: AsyncSession, docente: User) -> Preference:
    preferencia_result = await db.execute(select(Preference).where(Preference.user_id == docente.id))
    preferencia = preferencia_result.scalar_one_or_none()
    if not preferencia:
        preferencia = Preference(
            user_id=docente.id,
            educational_level_id=1,
            modality_id=1,
            location="CDMX",
            location_description="Zona centro"
        )
        db.add(preferencia)
        await db.flush()
        print("Preferencia creada.")
    else:
        print("La preferencia ya existe.")
    return preferencia

async def crear_docente():
    async with async_session() as db:
        # Docente base (usuario, perfil, preferencia)
        docente = await _ensure_docente_user(db)
        await _ensure_docente_profile(db, docente)
        preferencia = await _ensure_docente_preference(db, docente)

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
        # Alumno de prueba (módulo separado)
        # =====================
        alumno = await crear_alumno(db)

        # Obtener status_approved para los bookings
        status_approved = (await db.execute(select(Status).where(Status.name == "approved"))).scalar_one_or_none()

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
            # Crear slots de 1 hora desde 09:00 hasta 22:00 (último slot 21:00-22:00)
            for hour in range(9, 22):
                slot = Availability(
                    user_id=docente.id,
                    preference_id=preferencia.id,
                    day_of_week=day_info["day"],
                    start_time=f"{hour:02d}:00:00",
                    end_time=f"{hour+1:02d}:00:00",
                )
                db.add(slot)
                await db.flush()
                availabilities.append(slot)
            print(f"✅ Availabilities horarias creadas para {day_info['name']} (09:00-22:00)")

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
            
            # Buscar la availability que corresponde al día y hora exactos
            availability_for_day = None
            booking_slot_start_str = clase_inicio.strftime("%H:%M:%S")
            for avail in availabilities:
                if (
                    avail.day_of_week == booking_data["day_of_week"]
                    and str(avail.start_time) == booking_slot_start_str
                ):
                    availability_for_day = avail
                    break
            
            if not availability_for_day:
                print(f"❌ No se encontró availability para day_of_week={booking_data['day_of_week']} y hora {booking_slot_start_str}")
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

        # Buscar slot específico para Martes 09:00:00
        fixed_slot = None
        for avail in availabilities:
            if avail.day_of_week == 2 and str(avail.start_time) == "09:00:00":
                fixed_slot = avail
                break
        
        # Crear booking nuevo usando el slot correcto
        booking = Booking(
            user_id=alumno.id,
            availability_id=fixed_slot.id if fixed_slot else availabilities[0].id,
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

        # =====================
        # Reservas futuras adicionales (3 más)
        # =====================
        futuras_fechas = [
            datetime(2025, 12, 2),   # Martes
            datetime(2025, 12, 9),   # Martes
            datetime(2025, 12, 16),  # Martes
        ]

        for fecha_booking in futuras_fechas:
            # Siempre a las 09:00:00
            hora_inicio = datetime.strptime("09:00:00", "%H:%M:%S").time()
            clase_inicio = datetime.combine(fecha_booking.date(), hora_inicio)
            clase_fin = clase_inicio + timedelta(hours=1)

            # Buscar slot Martes 09:00:00
            future_slot = None
            for avail in availabilities:
                if avail.day_of_week == 2 and str(avail.start_time) == "09:00:00":
                    future_slot = avail
                    break

            # Crear booking
            future_booking = Booking(
                user_id=alumno.id,
                availability_id=future_slot.id if future_slot else availabilities[0].id,
                start_time=clase_inicio,
                end_time=clase_fin,
                status_id=status_approved.id if status_approved else None,
                class_space="zoom",
            )
            db.add(future_booking)
            await db.flush()
            print(f"✅ Booking futuro creado: {clase_inicio} - {clase_fin}")

            # PaymentBooking asociado
            total_amount = int(precio.selected_prices * 100)
            future_pay = PaymentBooking(
                user_id=alumno.id,
                booking_id=future_booking.id,
                price_id=precio.id,
                total_amount=total_amount,
                commission_percentage=0,
                commission_amount=0,
                teacher_amount=total_amount,
                platform_amount=0,
                status_id=status_approved.id if status_approved else None,
                stripe_payment_intent_id=f"pi_future_{clase_inicio.strftime('%Y_%m_%d')}",
            )
            db.add(future_pay)
            await db.flush()

            # Confirmation
            future_conf = Confirmation(
                teacher_id=docente.id,
                student_id=alumno.id,
                payment_booking_id=future_pay.id,
                confirmation_date_teacher=False,
                confirmation_date_student=False,
                description_teacher="Clase programada (futura)",
                description_student="Lista para clase futura",
            )
            db.add(future_conf)

        # =====================
        # Booking recientemente finalizado (≤ 2 horas desde su fin)
        # =====================
        now = datetime.now()
        # Ajustar fin a la hora en punto anterior (para coincidir con slots por hora)
        recent_end = now.replace(minute=0, second=0, microsecond=0)
        if recent_end >= now:
            # Si justo cae en la hora exacta, restar una hora para que quede "ya finalizado"
            recent_end = recent_end - timedelta(hours=1)
        recent_start = recent_end - timedelta(hours=1)

        # Determinar day_of_week con base en recent_start (1=Lunes ... 7=Domingo)
        day_of_week_recent = recent_start.weekday() + 1
        start_str = recent_start.strftime("%H:%M:%S")
        end_str = recent_end.strftime("%H:%M:%S")

        # Buscar o crear slot que coincida exactamente
        recent_slot = None
        for avail in availabilities:
            if avail.day_of_week == day_of_week_recent and str(avail.start_time) == start_str:
                recent_slot = avail
                break
        if not recent_slot:
            # Crear slot dinámico para este día/hora
            recent_slot = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=day_of_week_recent,
                start_time=start_str,
                end_time=end_str,
            )
            db.add(recent_slot)
            await db.flush()
            availabilities.append(recent_slot)
            print(f"🆕 Slot dinámico creado para booking reciente: DOW={day_of_week_recent} {start_str}-{end_str}")

        # Crear booking finalizado recientemente
        recent_booking = Booking(
            user_id=alumno.id,
            availability_id=recent_slot.id,
            start_time=recent_start,
            end_time=recent_end,
            status_id=status_approved.id if status_approved else None,
            class_space="zoom",
        )
        db.add(recent_booking)
        await db.flush()
        print(f"✅ Booking reciente finalizado: {recent_start} - {recent_end} (≤ 2h desde su fin)")

        # PaymentBooking para el booking reciente
        total_amount_recent = int(precio.selected_prices * 100)
        recent_pay = PaymentBooking(
            user_id=alumno.id,
            booking_id=recent_booking.id,
            price_id=precio.id,
            total_amount=total_amount_recent,
            commission_percentage=0,
            commission_amount=0,
            teacher_amount=total_amount_recent,
            platform_amount=0,
            status_id=status_approved.id if status_approved else None,
            stripe_payment_intent_id=f"pi_recent_{recent_start.strftime('%Y_%m_%d_%H')}",
        )
        db.add(recent_pay)
        await db.flush()

        # Confirmation del booking reciente (sin assessment al ser muy reciente)
        recent_conf = Confirmation(
            teacher_id=docente.id,
            student_id=alumno.id,
            payment_booking_id=recent_pay.id,
            confirmation_date_teacher=False,
            confirmation_date_student=False,
            description_teacher="Clase finalizada recientemente",
            description_student="Clase finalizada (reciente)",
        )
        db.add(recent_conf)

        # =====================
        # Booking finalizado hace ~1 hora
        # =====================
        onehour_end = recent_end - timedelta(hours=1)
        onehour_start = onehour_end - timedelta(hours=1)
        day_of_week_one = onehour_start.weekday() + 1
        one_start_str = onehour_start.strftime("%H:%M:%S")
        one_end_str = onehour_end.strftime("%H:%M:%S")

        one_slot = None
        for avail in availabilities:
            if avail.day_of_week == day_of_week_one and str(avail.start_time) == one_start_str:
                one_slot = avail
                break
        if not one_slot:
            one_slot = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=day_of_week_one,
                start_time=one_start_str,
                end_time=one_end_str,
            )
            db.add(one_slot)
            await db.flush()
            availabilities.append(one_slot)
            print(f"🆕 Slot dinámico creado (≈1h): DOW={day_of_week_one} {one_start_str}-{one_end_str}")

        one_booking = Booking(
            user_id=alumno.id,
            availability_id=one_slot.id,
            start_time=onehour_start,
            end_time=onehour_end,
            status_id=status_approved.id if status_approved else None,
            class_space="zoom",
        )
        db.add(one_booking)
        await db.flush()
        print(f"✅ Booking finalizado ≈1h: {onehour_start} - {onehour_end}")

        one_total_amount = int(precio.selected_prices * 100)
        one_pay = PaymentBooking(
            user_id=alumno.id,
            booking_id=one_booking.id,
            price_id=precio.id,
            total_amount=one_total_amount,
            commission_percentage=0,
            commission_amount=0,
            teacher_amount=one_total_amount,
            platform_amount=0,
            status_id=status_approved.id if status_approved else None,
            stripe_payment_intent_id=f"pi_recent_1h_{onehour_start.strftime('%Y_%m_%d_%H')}",
        )
        db.add(one_pay)
        await db.flush()

        one_conf = Confirmation(
            teacher_id=docente.id,
            student_id=alumno.id,
            payment_booking_id=one_pay.id,
            confirmation_date_teacher=False,
            confirmation_date_student=False,
            description_teacher="Clase finalizada (~1h)",
            description_student="Clase finalizada (~1h)",
        )
        db.add(one_conf)

        # =====================
        # Booking finalizado hace > 2 horas
        # =====================
        gt2_end = recent_end - timedelta(hours=3)
        gt2_start = gt2_end - timedelta(hours=1)
        day_of_week_gt2 = gt2_start.weekday() + 1
        gt2_start_str = gt2_start.strftime("%H:%M:%S")
        gt2_end_str = gt2_end.strftime("%H:%M:%S")

        gt2_slot = None
        for avail in availabilities:
            if avail.day_of_week == day_of_week_gt2 and str(avail.start_time) == gt2_start_str:
                gt2_slot = avail
                break
        if not gt2_slot:
            gt2_slot = Availability(
                user_id=docente.id,
                preference_id=preferencia.id,
                day_of_week=day_of_week_gt2,
                start_time=gt2_start_str,
                end_time=gt2_end_str,
            )
            db.add(gt2_slot)
            await db.flush()
            availabilities.append(gt2_slot)
            print(f"🆕 Slot dinámico creado (>2h): DOW={day_of_week_gt2} {gt2_start_str}-{gt2_end_str}")

        gt2_booking = Booking(
            user_id=alumno.id,
            availability_id=gt2_slot.id,
            start_time=gt2_start,
            end_time=gt2_end,
            status_id=status_approved.id if status_approved else None,
            class_space="zoom",
        )
        db.add(gt2_booking)
        await db.flush()
        print(f"✅ Booking finalizado >2h: {gt2_start} - {gt2_end}")

        gt2_total_amount = int(precio.selected_prices * 100)
        gt2_pay = PaymentBooking(
            user_id=alumno.id,
            booking_id=gt2_booking.id,
            price_id=precio.id,
            total_amount=gt2_total_amount,
            commission_percentage=0,
            commission_amount=0,
            teacher_amount=gt2_total_amount,
            platform_amount=0,
            status_id=status_approved.id if status_approved else None,
            stripe_payment_intent_id=f"pi_recent_gt2h_{gt2_start.strftime('%Y_%m_%d_%H')}",
        )
        db.add(gt2_pay)
        await db.flush()

        gt2_conf = Confirmation(
            teacher_id=docente.id,
            student_id=alumno.id,
            payment_booking_id=gt2_pay.id,
            confirmation_date_teacher=False,
            confirmation_date_student=False,
            description_teacher=">2h desde fin",
            description_student=">2h desde fin",
        )
        db.add(gt2_conf)

        await db.commit()
        print("Docente de prueba creado con documentos, video, alumno, booking, payment_booking, confirmation y assessment.")

# Seed orchestrator disabled; usar crear_docente() desde app/__init__.py
async def seed_all():
    return None
