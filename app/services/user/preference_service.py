from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from fastapi import HTTPException  
from app.models import Preference, EducationalLevel, Modality
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.user.preference_schema import (
    PreferenceUpdateRequest, 
    PreferenceCreateRequest
)

# ==================== VALIDACIONES ====================

async def _validate_user_exists(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El usuario con ID {user_id} no existe")

async def _validate_unique_preference(db: AsyncSession, user_id: int):
    result = await db.execute(select(Preference).where(Preference.user_id == user_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El usuario ya tiene preferencias asociadas")

def _validate_location(location: Optional[str]):
    if location and len(location.strip()) < 3:
        raise HTTPException(status_code=400, detail="La ubicación debe tener al menos 3 caracteres")

def _validate_location_description(description: Optional[str]):
    if description and len(description.strip()) > 200:
        raise HTTPException(status_code=400, detail="La descripción no puede exceder los 200 caracteres")

async def get_preference_by_user_id(db: AsyncSession, user_id: int) -> Optional[Preference]:
    result = await db.execute(select(Preference).where(Preference.user_id == user_id))
    return result.scalar_one_or_none()

async def _get_existing_preference_or_404(db: AsyncSession, user_id: int) -> Preference:
    preference = await get_preference_by_user_id(db, user_id)
    if not preference:
        raise HTTPException(status_code=404, detail="Preferencias no encontradas")
    return preference

# ==================== FUNCIONES PRINCIPALES ====================

async def get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return user_id

async def create_preference_by_token(
    db: AsyncSession,
    token: str,
    preference_data: PreferenceCreateRequest
) -> Preference:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)
    await _validate_unique_preference(db, user_id)

    edu_level = await db.get(EducationalLevel, preference_data.educational_level_id)
    if not edu_level:
        raise HTTPException(status_code=404, detail="Nivel educativo no encontrado")
    
    modality = await db.get(Modality, preference_data.modality_id)
    if not modality:
        raise HTTPException(status_code=404, detail="Modalidad no encontrada")

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
    user_id = await get_user_id_from_token(token)
    return await _get_existing_preference_or_404(db, user_id)

async def update_preference_by_token(
    db: AsyncSession,
    token: str,
    update_data: PreferenceUpdateRequest
) -> Preference:
    user_id = await get_user_id_from_token(token)
    preference = await _get_existing_preference_or_404(db, user_id)

    if update_data.educational_level_id is not None:
        edu_level = await db.get(EducationalLevel, update_data.educational_level_id)
        if not edu_level:
            raise HTTPException(status_code=404, detail="Nivel educativo no encontrado")
        preference.educational_level_id = update_data.educational_level_id

    if update_data.modality_id is not None:
        modality = await db.get(Modality, update_data.modality_id)
        if not modality:
            raise HTTPException(status_code=404, detail="Modalidad no encontrada")
        preference.modality_id = update_data.modality_id

    if update_data.location is not None:
        _validate_location(update_data.location)
        preference.location = update_data.location

    if update_data.location_description is not None:
        _validate_location_description(update_data.location_description)
        preference.location_description = update_data.location_description

    preference.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(preference)
    return preference
