from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.apis.deps import auth_required
from app.apis.deps import get_db, require_privilege
from app.services.user.profile_service import ProfileService
from app.schemas.user.profile_schema import ProfileCreateRequest, ProfileUpdateRequest, ProfileResponse, ProfileListResponse

router = APIRouter()

@router.post("/create/", response_model=ProfileResponse, dependencies=[Depends(auth_required)])
async def create_profile(
    profile_data: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Crear un nuevo perfil
    """
    try:
        profile_service = ProfileService(db)
        profile = await profile_service.create_profile(profile_data)
        return ProfileResponse(
            success=True,
            message="Perfil creado exitosamente",
            data=profile
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear el perfil: {str(e)}"
        )

@router.get("/search/{profile_id}", response_model=ProfileResponse, dependencies=[Depends(auth_required)])
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Consultar un perfil por ID
    """
    try:
        profile_service = ProfileService(db)
        profile = await profile_service.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil no encontrado"
            )
        return ProfileResponse(
            success=True,
            message="Perfil encontrado",
            data=profile
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar el perfil: {str(e)}"
        )

@router.put("/update/{profile_id}", response_model=ProfileResponse, dependencies=[Depends(auth_required)])
async def update_profile(
    profile_id: int,
    profile_data: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Editar un perfil existente
    """
    try:
        profile_service = ProfileService(db)
        profile = await profile_service.update_profile(profile_id, profile_data)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil no encontrado"
            )
        return ProfileResponse(
            success=True,
            message="Perfil actualizado exitosamente",
            data=profile
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al actualizar el perfil: {str(e)}"
        )