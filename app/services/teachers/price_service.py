from sqlalchemy import select
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

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
    _validate_selected_price_within_range(price_data.selected_prices, price_data.price_range_id)

    # Calcular extra_hour_price automáticamente
    auto_extra_price = round(price_data.selected_prices / 2, 2)

    # Crear registro de precio
    db_price = Price(
        user_id=user_id,
        preference_id=price_data.preference_id,
        price_range_id=price_data.price_range_id,
        selected_prices=price_data.selected_prices,
        extra_hour_price=auto_extra_price,
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
