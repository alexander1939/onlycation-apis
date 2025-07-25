from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.models import Preference
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.user.preference_schema import (
    PreferenceUpdateRequest, 
    PreferenceCreateRequest
)

# ==================== VALIDACIONES ====================

async def _validate_user_exists(db: AsyncSession, user_id: int):
    """Valida que el usuario exista en la base de datos"""
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise ValueError(f"El usuario con ID {user_id} no existe")

async def _validate_unique_preference(db: AsyncSession, user_id: int):
    """Valida que el usuario no tenga ya preferencias"""
    result = await db.execute(select(Preference).where(Preference.user_id == user_id))
    if result.scalar_one_or_none():
        raise ValueError("El usuario ya tiene preferencias asociadas")

def _validate_location(location: Optional[str]):
    """Valida la ubicación"""
    if location and len(location.strip()) < 3:
        raise ValueError("La ubicación debe tener al menos 3 caracteres")

def _validate_location_description(description: Optional[str]):
    """Valida la descripción de ubicación"""
    if description and len(description.strip()) > 200:
        raise ValueError("La descripción no puede exceder los 200 caracteres")

async def get_preference_by_user_id(db: AsyncSession, user_id: int) -> Optional[Preference]:
    """Obtiene las preferencias por ID de usuario"""
    result = await db.execute(select(Preference).where(Preference.user_id == user_id))
    return result.scalar_one_or_none()

async def _get_existing_preference_or_404(db: AsyncSession, user_id: int) -> Preference:
    """Valida que las preferencias existan, si no lanza error"""
    preference = await get_preference_by_user_id(db, user_id)
    if not preference:
        raise ValueError("Preferencias no encontradas")
    return preference

# ==================== FUNCIONES PRINCIPALES ====================

async def get_user_id_from_token(token: str) -> int:
    """Extrae y valida el user_id del token"""
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    return user_id

async def create_preference_by_token(
    db: AsyncSession,
    token: str,
    preference_data: PreferenceCreateRequest
) -> Preference:
    """
    Crea preferencias usando el token JWT

    Raises:
        ValueError: Si el token es inválido, el usuario no existe o ya tiene preferencias.
    """
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)
    await _validate_unique_preference(db, user_id)

    _validate_location(preference_data.location)
    _validate_location_description(preference_data.location_description)

    db_preference = Preference(
        user_id=user_id,
        educational_level_id=preference_data.educational_level_id,
        modality_id=preference_data.modality_id,
        location=preference_data.location,
        location_description=preference_data.location_description
    )

    db.add(db_preference)
    await db.commit()
    await db.refresh(db_preference)
    return db_preference

async def get_preference_by_token(db: AsyncSession, token: str) -> Preference:
    """
    Obtiene las preferencias usando el token JWT

    Raises:
        ValueError: Si el token es inválido o no hay preferencias asociadas.
    """
    user_id = await get_user_id_from_token(token)
    return await _get_existing_preference_or_404(db, user_id)

async def update_preference_by_token(
    db: AsyncSession,
    token: str,
    update_data: PreferenceUpdateRequest
) -> Preference:
    """
    Actualiza las preferencias usando el token JWT

    Raises:
        ValueError: Si el token es inválido o las preferencias no existen.
    """
    user_id = await get_user_id_from_token(token)
    preference = await _get_existing_preference_or_404(db, user_id)

    update_values = update_data.model_dump(exclude_unset=True)
    for field, value in update_values.items():
        setattr(preference, field, value)

    preference.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(preference)
    return preference