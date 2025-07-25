from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.deps import auth_required, get_db
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
    update_preference_by_token
)


security = HTTPBearer()
router = APIRouter()

"""
    Crea preferencias para el usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Un usuario solo puede tener un registro de preferencias
    - Devuelve los datos básicos de las preferencias creadas
"""
@router.post("/create/", 
            response_model=PreferenceCreateResponse,
            dependencies=[Depends(auth_required)])
async def create_my_preferences(
    preference_data: PreferenceCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

"""
    Obtiene las preferencias del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Devuelve todos los campos de las preferencias
"""
@router.get("/update/me/", 
           response_model=PreferenceResponse,
           dependencies=[Depends(auth_required)])
async def get_my_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

"""
    Actualiza las preferencias del usuario autenticado
    - Usa el token JWT para identificar al usuario
    - Actualiza solo los campos proporcionados
    - Devuelve solo los campos relevantes para actualización
"""
@router.put("/my_preferences/",
           response_model=PreferenceUpdateResponse,
           dependencies=[Depends(auth_required)])
async def update_my_preferences(
    preference_data: PreferenceUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )