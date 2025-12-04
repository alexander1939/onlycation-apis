from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException
from app.models.users.user import User
from app.schemas.user.user_schema import UserUpdateRequest

async def update_user_name(
    db: AsyncSession,
    user_id: int,
    update_data: UserUpdateRequest
) -> User:
    """
    Actualiza el nombre y/o apellido de un usuario
    """
    # Verificar que el usuario existe
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Preparar los datos a actualizar
    update_values = {}
    if update_data.first_name is not None:
        update_values['first_name'] = update_data.first_name
    if update_data.last_name is not None:
        update_values['last_name'] = update_data.last_name
    
    # Si no hay nada que actualizar, retornar el usuario actual
    if not update_values:
        return user
    
    # Actualizar los datos del usuario
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_values)
    )
    
    await db.execute(stmt)
    await db.commit()  # Asegurar que los cambios se guarden
    await db.refresh(user)  # Actualizar el objeto con los últimos datos
    return user


async def get_user_by_id(
    db: AsyncSession,
    user_id: int
) -> User:
    """
    Obtiene un usuario por su ID
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return user
