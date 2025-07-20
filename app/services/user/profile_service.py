from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.models.users.profile import Profile
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.user.profile_schema import ProfileUpdateRequest

# ==================== VALIDACIONES ====================

async def _validate_user_exists(db: AsyncSession, user_id: int):
    """Valida que el usuario exista en la base de datos"""
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise ValueError(f"El usuario con ID {user_id} no existe")

async def _validate_unique_profile(db: AsyncSession, user_id: int):
    """Valida que el usuario no tenga ya un perfil"""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    if result.scalar_one_or_none():
        raise ValueError("El usuario ya tiene un perfil asociado")

def _validate_credential(credential: Optional[str]):
    """Valida la credencial profesional"""
    if credential and len(credential.strip()) < 3:
        raise ValueError("La credencial debe tener al menos 3 caracteres")

def _validate_gender(gender: Optional[str]):
    """Valida el género del perfil"""
    valid_genders = ["Masculino", "Femenino", "No binario", "Otro"]
    if gender and gender not in valid_genders:
        raise ValueError(f"Género inválido. Opciones: {', '.join(valid_genders)}")

def _validate_sex(sex: Optional[str]):
    """Valida el sexo del perfil"""
    valid_sexes = ["Hombre", "Mujer", "Intersexual"]
    if sex and sex not in valid_sexes:
        raise ValueError(f"Sexo inválido. Opciones: {', '.join(valid_sexes)}")

async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Optional[Profile]:
    """Obtiene el perfil por ID de usuario (para usar con token)"""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()

# ==================== FUNCIONES PRINCIPALES ====================

async def create_profile(db: AsyncSession, profile_data) -> Profile:
    """
    Crea un nuevo perfil de usuario con validaciones
    - Valida que el usuario exista y no tenga perfil
    - Verifica credencial, género y sexo
    - Crea el registro en la base de datos
    """
    # Validaciones
    await _validate_user_exists(db, profile_data.user_id)
    await _validate_unique_profile(db, profile_data.user_id)
    _validate_credential(profile_data.credential)
    _validate_gender(profile_data.gender)
    _validate_sex(profile_data.sex)

    # Creación del perfil
    db_profile = Profile(
        user_id=profile_data.user_id,
        credential=profile_data.credential.strip() if profile_data.credential else None,
        gender=profile_data.gender,
        sex=profile_data.sex
    )
    
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    return db_profile



async def get_profile_by_token(db: AsyncSession, token: str) -> Profile:
    """
    Obtiene el perfil usando el token JWT
    - Valida el token
    - Verifica la existencia del usuario
    - Comprueba que exista el perfil
    - Todas las validaciones están aquí
    """
    payload = verify_token(token)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    
    profile = await get_profile_by_user_id(db, user_id)
    
    if not profile:
        raise ValueError("Perfil no encontrado")
    
    return profile



async def update_profile_by_token(
    db: AsyncSession, 
    token: str,
    update_data: ProfileUpdateRequest
) -> Profile:
    """
    Actualiza el perfil usando el token JWT
    - Valida el token
    - Obtiene el user_id
    - Actualiza el perfil asociado
    """
    # Verificar token y obtener user_id
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    
    # Obtener el perfil existente
    profile = await get_profile_by_user_id(db, user_id)
    if not profile:
        raise ValueError("Perfil no encontrado")
    
    # Aplicar actualizaciones
    update_values = update_data.model_dump(exclude_unset=True)
    for field, value in update_values.items():
        setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(profile)
    return profile