from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from fastapi import HTTPException  
from app.models.users.profile import Profile
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.user.profile_schema import ProfileUpdateRequest, ProfileCreateRequest

# ==================== VALIDACIONES ====================

async def _validate_user_exists(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El usuario con ID {user_id} no existe")

async def _validate_unique_profile(db: AsyncSession, user_id: int):
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El usuario ya tiene un perfil asociado")

def _validate_credential(credential: Optional[str]):
    if credential and len(credential.strip()) < 3:
        raise HTTPException(status_code=400, detail="La credencial debe tener al menos 3 caracteres")

def _validate_gender(gender: Optional[str]):
    valid_genders = ["Masculino", "Femenino", "No binario", "Otro"]
    if gender and gender not in valid_genders:
        raise HTTPException(
            status_code=400,
            detail=f"Género inválido. Opciones válidas: {', '.join(valid_genders)}"
        )

def _validate_sex(sex: Optional[str]):
    valid_sexes = ["Hombre", "Mujer", "Intersexual"]
    if sex and sex not in valid_sexes:
        raise HTTPException(
            status_code=400,
            detail=f"Sexo inválido. Opciones válidas: {', '.join(valid_sexes)}"
        )

async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Optional[Profile]:
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()

async def _get_existing_profile_or_404(db: AsyncSession, user_id: int) -> Profile:
    profile = await get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return profile

# ==================== FUNCIONES PRINCIPALES ====================

async def get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return user_id

async def create_profile_by_token(
    db: AsyncSession,
    token: str,
    profile_data: ProfileCreateRequest
) -> Profile:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)
    await _validate_unique_profile(db, user_id)

    _validate_credential(profile_data.credential)
    _validate_gender(profile_data.gender)
    _validate_sex(profile_data.sex)

    db_profile = Profile(
        user_id=user_id,
        credential=profile_data.credential,
        gender=profile_data.gender,
        sex=profile_data.sex
    )

    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def get_profile_by_token(db: AsyncSession, token: str) -> Profile:
    user_id = await get_user_id_from_token(token)
    return await _get_existing_profile_or_404(db, user_id)

async def update_profile_by_token(
    db: AsyncSession,
    token: str,
    update_data: ProfileUpdateRequest
) -> Profile:
    user_id = await get_user_id_from_token(token)
    profile = await _get_existing_profile_or_404(db, user_id)

    update_values = update_data.model_dump(exclude_unset=True)

    # Validaciones condicionales antes de asignar
    if "credential" in update_values:
        _validate_credential(update_values["credential"])
    if "gender" in update_values:
        _validate_gender(update_values["gender"])
    if "sex" in update_values:
        _validate_sex(update_values["sex"])

    for field, value in update_values.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(profile)
    return profile
