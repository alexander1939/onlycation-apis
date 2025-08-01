from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.deps import auth_required, get_db
from app.schemas.user.profile_schema import ProfileCreateRequest, ProfileUpdateRequest, ProfileData, ProfileResponse, ProfileCreateData, ProfileCreateResponse, ProfileUpdateData, ProfileUpdateResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer()
router = APIRouter()


from app.services.user.profile_service import (
    create_profile_by_token,
     get_profile_by_token,
    update_profile_by_token
)


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