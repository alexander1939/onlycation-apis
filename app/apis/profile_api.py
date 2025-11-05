from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.deps import auth_required, get_db
from app.schemas.user.profile_schema import ProfileCreateRequest, ProfileUpdateRequest, ProfileData, ProfileResponse, ProfileCreateData, ProfileCreateResponse, ProfileUpdateData, ProfileUpdateResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.user.preference_schema import (
    PreferenceCreateRequest,
    PreferenceCreateResponse,
    PreferenceCreateData,
    PreferenceResponse,
    PreferenceData,
    PreferenceUpdateRequest,
    PreferenceUpdateResponse,
    PreferenceUpdateData
)
from app.services.user.preference_service import (
    create_preference_by_token,
    get_preference_by_token,
    update_preference_by_token,
    get_user_id_from_token
)

from app.services.user.profile_service import (
    create_profile_by_token,
     get_profile_by_token,
    update_profile_by_token
)

security = HTTPBearer()
router = APIRouter()


"""
    Crea un nuevo perfil para el usuario autenticado
    - Requiere token JWT válido
    - El user_id se obtiene del token automáticamente
    - Valida los datos del perfil
    """
@router.post("/create/", 
            response_model=ProfileCreateResponse,
            dependencies=[Depends(auth_required)])  
async def create_profile_route(
    profile_data: ProfileCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),  
    db: AsyncSession = Depends(get_db)
):
    
    token = credentials.credentials  
    profile = await create_profile_by_token(db, token, profile_data)  
    
    return ProfileCreateResponse(
        success=True,
        message="Perfil creado exitosamente",
        data=ProfileCreateData(
            credential=profile.credential,
            gender=profile.gender,
            sex=profile.sex,
            created_at=profile.created_at
        )
    )

"""
    Actualiza el perfil del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Actualiza solo los campos proporcionados
    - Devuelve solo los campos relevantes para actualización
    """
@router.put("/update/me/", 
           response_model=ProfileUpdateResponse,
           dependencies=[Depends(auth_required)])
async def update_my_profile(
    profile_data: ProfileUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    
    token = credentials.credentials
    profile = await update_profile_by_token(db, token, profile_data)
    
    return ProfileUpdateResponse(
        success=True,
        message="Perfil actualizado exitosamente",
        data=ProfileUpdateData(
            credential=profile.credential,
            gender=profile.gender,
            sex=profile.sex,
            updated_at=profile.updated_at
        )
    )


"""
    Obtiene el perfil del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Devuelve los datos en formato ProfileResponse
    """
@router.get("/my_profile/", response_model=ProfileResponse, dependencies=[Depends(auth_required)])
async def get_my_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    
    token = credentials.credentials
    profile = await get_profile_by_token(db, token)
    
    return ProfileResponse(
        success=True,
        message="Perfil obtenido exitosamente",
        data=ProfileData(
            credential=profile.credential,
            gender=profile.gender,
            sex=profile.sex,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    )


"""
    Crea preferencias para el usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Un usuario solo puede tener un registro de preferencias
    - Devuelve los datos básicos de las preferencias creadas
"""
@router.post("/preferences/create/",
            response_model=PreferenceCreateResponse,
            dependencies=[Depends(auth_required)])
async def create_my_preferences(
    preference_data: PreferenceCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
        token = credentials.credentials
        preference = await create_preference_by_token(db, token, preference_data)
        
        return PreferenceCreateResponse(
            success=True,
            message="Preferencias creadas exitosamente",
            data=PreferenceCreateData(
                educational_level_id=preference.educational_level_id,
                modality_id=preference.modality_id,
                location=preference.location,
                location_description=preference.location_description,
                created_at=preference.created_at
            )
        )



"""
    Actualiza las preferencias del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Actualiza solo los campos proporcionados
    - Devuelve solo los campos relevantes para actualización
"""
@router.put("/preferences/update/me/",
           response_model=PreferenceUpdateResponse,
           dependencies=[Depends(auth_required)])
async def update_my_preferences(
    preference_data: PreferenceUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
        token = credentials.credentials
        preference = await update_preference_by_token(db, token, preference_data)
        
        return PreferenceUpdateResponse(
            success=True,
            message="Preferencias actualizadas exitosamente",
            data=PreferenceUpdateData(
                educational_level_id=preference.educational_level_id,
                modality_id=preference.modality_id,
                location=preference.location,
                location_description=preference.location_description,
                updated_at=preference.updated_at
            )
        )

    

"""
    Obtiene las preferencias del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Devuelve todos los campos de las preferencias
"""
@router.get("/preferences/me/",
           response_model=PreferenceResponse,
           dependencies=[Depends(auth_required)])
async def get_my_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):

        token = credentials.credentials
        preference = await get_preference_by_token(db, token)
        
        return PreferenceResponse(
            success=True,
            message="Preferencias obtenidas exitosamente",
            data=PreferenceData(
                educational_level_id=preference.educational_level_id,
                modality_id=preference.modality_id,
                location=preference.location,
                location_description=preference.location_description,
                created_at=preference.created_at,
                updated_at=preference.updated_at
            )
        )


"""
    Obtiene el nivel educativo del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Devuelve el nombre del nivel educativo
"""
@router.get("/preferences/educational_level/",
           dependencies=[Depends(auth_required)])
async def get_educational_level(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    preference = await get_preference_by_token(db, token)
    
    # Cargar la relación del nivel educativo
    await db.refresh(preference, ["educational_level"])
    
    return {
        "success": True,
        "message": "Nivel educativo obtenido exitosamente",
        "data": {
            "educational_level": preference.educational_level.name if preference.educational_level else None
        }
    }
