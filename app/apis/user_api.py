from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer
from sqlalchemy import select
from app.models.users.user import User
from app.apis.deps import get_db, auth_required
from app.schemas.user.user_schema import UserUpdateRequest, UserResponse
from app.services.user.user_service import update_user_name, get_user_by_id


security = HTTPBearer()
router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener datos del usuario",
    description="Obtiene los datos del usuario autenticado"
)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtiene los datos del usuario autenticado
    """
    user_id = user_data.get("user_id")
    user = await get_user_by_id(db, user_id)
    return user

@router.patch(
    "/me/name",
    response_model=UserResponse,
    summary="Actualizar nombre y apellido del usuario",
    description="Actualiza el nombre y/o apellido del usuario autenticado"
)
async def update_user_name_endpoint(
    update_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Actualiza el nombre y/o apellido del usuario autenticado.
    
    - **first_name**: Nuevo nombre (opcional)
    - **last_name**: Nuevo apellido (opcional)
    
    Al menos uno de los campos debe ser proporcionado.
    """
    # Verificar que al menos un campo fue proporcionado
    if update_data.first_name is None and update_data.last_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se debe proporcionar al menos un campo para actualizar (first_name o last_name)"
        )
    
    # Obtener el ID del usuario del token
    user_id = user_data.get("user_id")
    
    # Actualizar el nombre del usuario
    updated_user = await update_user_name(db, user_id, update_data)
    return updated_user
