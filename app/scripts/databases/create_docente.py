from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.users.user import User
from app.models.users.profile import Profile
from app.models.users.preference import Preference
from app.models.teachers.price import Price
from app.models.teachers.availability import Availability
from sqlalchemy import select
from datetime import datetime, timedelta
from app.models.common.stripe_price import StripePrice
from app.external.stripe_config import stripe_config
import stripe
from app.cores.security import get_password_hash



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
        disponibilidad = Availability(
            user_id=docente.id,
            preference_id=preferencia.id,
            day_of_week=1,  # Lunes
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2)
        )
        db.add(disponibilidad)
        print("Disponibilidad creada.")

        await db.commit()
        print("Docente de prueba creado con datos relacionados.")
