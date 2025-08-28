from sqlalchemy import select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

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

def _validate_selected_price_within_range(selected_price: float, price_range_id: int):
    ranges = {
        1: (100, 800),    # preparatoria
        2: (200, 1200),   # universidad
        3: (300, 1500)    # posgrados
    }

    if price_range_id not in ranges:
        raise ValueError("Rango de precios no válido")

    min_price, max_price = ranges[price_range_id]
    if not (min_price <= selected_price <= max_price):
        raise ValueError(f"El precio debe estar entre ${min_price} y ${max_price} para este rango")

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
    _validate_selected_price_within_range(price_data.selected_prices, price_data.price_range_id)

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
