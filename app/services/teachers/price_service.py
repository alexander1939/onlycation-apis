from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc

import stripe
from app.models.common.stripe_price import StripePrice
from app.models import Price, Preference, PriceRange, User
from app.schemas.teachers.price_schema import PriceCreateRequest
from app.cores.token import verify_token

# ==================== VALIDACIONES ====================

async def _validate_user_exists(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise ValueError(f"El usuario con ID {user_id} no existe")

async def _validate_price_range_exists(db: AsyncSession, price_range_id: int):
    result = await db.execute(select(PriceRange).where(PriceRange.id == price_range_id))
    if not result.scalar_one_or_none():
        raise ValueError("El rango de precios no existe")

async def _validate_preference_exists(db: AsyncSession, preference_id: int, user_id: int):
    result = await db.execute(
        select(Preference).where(Preference.id == preference_id, Preference.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise ValueError("La preferencia no existe o no pertenece al usuario")

async def _validate_unique_price(db: AsyncSession, user_id: int):
    result = await db.execute(select(Price).where(Price.user_id == user_id))
    if result.scalar_one_or_none():
        raise ValueError("Ya has registrado un precio previamente")

async def _validate_selected_price_within_range(db: AsyncSession, selected_price: float, price_range_id: int):
    """Valida contra la base de datos que el precio seleccionado esté dentro del rango (min/max)
    configurado en la tabla PriceRange para el ID dado.
    """
    result = await db.execute(select(PriceRange).where(PriceRange.id == price_range_id))
    price_range = result.scalar_one_or_none()
    if not price_range:
        raise ValueError("El rango de precios no existe")

    # Convertir a float para comparación simple (DB suele ser Decimal)
    try:
        min_price = float(price_range.minimum_price)
        max_price = float(price_range.maximum_price)
    except Exception:
        raise ValueError("Rango de precios inválido en la base de datos")

    if not (min_price <= float(selected_price) <= max_price):
        raise ValueError(f"El precio debe estar entre ${min_price:.2f} y ${max_price:.2f} para este rango")

async def _validate_price_range_matches_educational_level(
    db: AsyncSession,
    price_range_id: int,
    preference_id: int
):
    # Obtener el educational_level_id de la preferencia
    pref_result = await db.execute(
        select(Preference.educational_level_id).where(Preference.id == preference_id)
    )
    pref_level_id = pref_result.scalar_one_or_none()
    if not pref_level_id:
        raise ValueError("No se encontró el nivel educativo de la preferencia")

    # Obtener el educational_level_id del rango de precios
    range_result = await db.execute(
        select(PriceRange.educational_level_id).where(PriceRange.id == price_range_id)
    )
    range_level_id = range_result.scalar_one_or_none()
    if not range_level_id:
        raise ValueError("No se encontró el nivel educativo del rango de precios")

    # Comparar los niveles educativos
    if pref_level_id != range_level_id:
        raise ValueError("El rango de precios no corresponde al nivel educativo seleccionado")

# ==================== FUNCIONES PRINCIPALES ====================

async def get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    return user_id

async def create_price_by_token(
    db: AsyncSession,
    token: str,
    price_data: PriceCreateRequest
) -> Price:
    user_id = await get_user_id_from_token(token)

    # Validaciones
    await _validate_user_exists(db, user_id)
    await _validate_unique_price(db, user_id)
    await _validate_price_range_exists(db, price_data.price_range_id)
    await _validate_preference_exists(db, price_data.preference_id, user_id)
    await _validate_price_range_matches_educational_level(db, price_data.price_range_id, price_data.preference_id)
    await _validate_selected_price_within_range(db, price_data.selected_prices, price_data.price_range_id)

    # Calcular extra_hour_price automáticamente
    auto_extra_price = round(price_data.selected_prices / 2, 2)
    tipo = "tutorias"
    currency = "mxn"

    # Buscar o crear StripePrice para el precio principal
    stripe_price_result = await db.execute(
        select(StripePrice).where(
            StripePrice.amount == price_data.selected_prices,
            StripePrice.type == tipo
        )
    )
    stripe_price_entry = stripe_price_result.scalar_one_or_none()

    if not stripe_price_entry:
        product = stripe.Product.create(
            name=f"Tutoría precio {price_data.selected_prices}",
            description="Pago por tutoría individual"
        )
        price = stripe.Price.create(
            unit_amount=int(price_data.selected_prices * 100),
            currency=currency,
            product=product.id
        )
        stripe_price_entry = StripePrice(
            stripe_product_id=product.id,
            stripe_price_id=price.id,
            amount=price_data.selected_prices,
            currency=currency,
            type=tipo
        )
        db.add(stripe_price_entry)
        await db.flush()

    # Buscar o crear StripePrice para el precio extra hora
    stripe_extra_result = await db.execute(
        select(StripePrice).where(
            StripePrice.amount == auto_extra_price,
            StripePrice.type == tipo
        )
    )
    stripe_extra_entry = stripe_extra_result.scalar_one_or_none()

    if not stripe_extra_entry:
        product_extra = stripe.Product.create(
            name=f"Tutoría precio {auto_extra_price}",
            description="Pago por hora extra de tutoría"
        )
        price_extra = stripe.Price.create(
            unit_amount=int(auto_extra_price * 100),
            currency=currency,
            product=product_extra.id
        )
        stripe_extra_entry = StripePrice(
            stripe_product_id=product_extra.id,
            stripe_price_id=price_extra.id,
            amount=auto_extra_price,
            currency=currency,
            type=tipo
        )
        db.add(stripe_extra_entry)
        await db.flush()

    # Crear registro de precio
    db_price = Price(
        user_id=user_id,
        preference_id=price_data.preference_id,
        price_range_id=price_data.price_range_id,
        selected_prices=price_data.selected_prices,
        extra_hour_price=auto_extra_price,
        stripe_product_id=stripe_price_entry.stripe_product_id,
        stripe_price_id=stripe_price_entry.stripe_price_id,
        stripe_extra_product_id=stripe_extra_entry.stripe_product_id,
        stripe_extra_price_id=stripe_extra_entry.stripe_price_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_price)
    await db.commit()
    await db.refresh(db_price)
    return db_price

async def get_prices_by_token(db: AsyncSession, token: str) -> list[Price]:
    user_id = await get_user_id_from_token(token)
    result = await db.execute(select(Price).where(Price.user_id == user_id))
    return result.scalars().all()

async def get_price_availability_by_token(db: AsyncSession, token: str) -> dict:
    """
    Resolve the user's latest Preference and fetch all PriceRanges available
    for that educational_level. Returns a dict with preference_id,
    educational_level_id and price_ranges (list of dicts).
    """
    user_id = await get_user_id_from_token(token)

    # Get latest preference for this user (by created_at desc)
    pref_q = await db.execute(
        select(Preference).where(Preference.user_id == user_id).order_by(desc(Preference.created_at))
    )
    preference = pref_q.scalars().first()
    if not preference:
        raise ValueError("El usuario no tiene preferencias registradas")

    # Fetch price ranges by the preference's educational level
    ranges_q = await db.execute(
        select(PriceRange).where(PriceRange.educational_level_id == preference.educational_level_id)
    )
    ranges = ranges_q.scalars().all()

    return {
        "preference_id": preference.id,
        "educational_level_id": preference.educational_level_id,
        "price_ranges": [
            {
                "id": r.id,
                "minimum_price": r.minimum_price,
                "maximum_price": r.maximum_price,
            }
            for r in ranges
        ],
    }

async def update_price_by_token(
    db: AsyncSession,
    token: str,
    selected_prices: float,
    price_range_id: int | None = None,
) -> Price:
    """Actualiza el precio base del docente autenticado con las reglas:
    - Solo el dueño (token) puede actualizar su precio.
    - Enfriamiento de 30 días desde el último cambio (updated_at o created_at).
    - Validaciones iguales a create: dentro del rango y correspondiente al nivel educativo de su preferencia.
    - No afecta reservas/pagos anteriores (no se tocan PaymentBooking existentes).
    - Recalcula extra_hour_price = selected_prices / 2 y mapea a StripePrice (reusa o crea).
    """
    user_id = await get_user_id_from_token(token)

    # Obtener registro Price existente
    res = await db.execute(select(Price).where(Price.user_id == user_id))
    price_obj: Price | None = res.scalars().one_or_none()
    if not price_obj:
        raise ValueError("No tienes un precio registrado aún. Debes crearlo primero.")

    # Verificar cooldown de 30 días
    # last_change = price_obj.updated_at or price_obj.created_at
    # if not last_change:
    #     # fallback defensivo: si no hay timestamps, bloquear
    #     raise ValueError("No es posible actualizar el precio en este momento (timestamps inválidos)")
    now = datetime.now(timezone.utc)
    # # Normalizar tz si fuera naive
    # if last_change.tzinfo is None:
    #     last_change = last_change.replace(tzinfo=timezone.utc)
    # if (now - last_change) < timedelta(days=30):
    #     raise ValueError("Solo puedes actualizar tu precio cada 30 días desde el último cambio")

    # Resolver rango objetivo: si no se envía, mantener el actual
    target_range_id = int(price_range_id) if price_range_id is not None else int(price_obj.price_range_id)

    # Validaciones: rango existe, corresponde al nivel educativo de su preferencia y precio dentro del rango
    await _validate_price_range_exists(db, target_range_id)
    await _validate_price_range_matches_educational_level(db, target_range_id, price_obj.preference_id)
    await _validate_selected_price_within_range(db, selected_prices, target_range_id)

    # Calcular extra hour auto
    auto_extra_price = round(selected_prices / 2, 2)
    tipo = "tutorias"
    currency = "mxn"

    # StripePrice para precio base
    sp_base_res = await db.execute(
        select(StripePrice).where(StripePrice.amount == selected_prices, StripePrice.type == tipo)
    )
    sp_base = sp_base_res.scalar_one_or_none()
    if not sp_base:
        product = stripe.Product.create(
            name=f"Tutoría precio {selected_prices}",
            description="Pago por tutoría individual",
        )
        price_created = stripe.Price.create(
            unit_amount=int(selected_prices * 100),
            currency=currency,
            product=product.id,
        )
        sp_base = StripePrice(
            stripe_product_id=product.id,
            stripe_price_id=price_created.id,
            amount=selected_prices,
            currency=currency,
            type=tipo,
        )
        db.add(sp_base)
        await db.flush()

    # StripePrice para extra hour
    sp_extra_res = await db.execute(
        select(StripePrice).where(StripePrice.amount == auto_extra_price, StripePrice.type == tipo)
    )
    sp_extra = sp_extra_res.scalar_one_or_none()
    if not sp_extra:
        product_extra = stripe.Product.create(
            name=f"Tutoría precio {auto_extra_price}",
            description="Pago por hora extra de tutoría",
        )
        price_extra_created = stripe.Price.create(
            unit_amount=int(auto_extra_price * 100),
            currency=currency,
            product=product_extra.id,
        )
        sp_extra = StripePrice(
            stripe_product_id=product_extra.id,
            stripe_price_id=price_extra_created.id,
            amount=auto_extra_price,
            currency=currency,
            type=tipo,
        )
        db.add(sp_extra)
        await db.flush()

    # Actualizar Price existente
    price_obj.selected_prices = selected_prices
    price_obj.extra_hour_price = auto_extra_price
    price_obj.price_range_id = target_range_id
    price_obj.stripe_product_id = sp_base.stripe_product_id
    price_obj.stripe_price_id = sp_base.stripe_price_id
    price_obj.stripe_extra_product_id = sp_extra.stripe_product_id
    price_obj.stripe_extra_price_id = sp_extra.stripe_price_id
    # updated_at se actualizará por onupdate=func.now(), pero seteamos por seguridad
    price_obj.updated_at = now

    await db.commit()
    await db.refresh(price_obj)
    return price_obj
