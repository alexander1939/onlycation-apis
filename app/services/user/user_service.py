from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from typing import Optional
from app.models.users.user import User
from app.schemas.user.user_schema import UserUpdateRequest

# ==================== VALIDACIONES ====================

def _format_name(name: str) -> str:
    """
    Formatea un nombre o apellido para que la primera letra de cada palabra sea mayúscula
    y el resto minúsculas.
    """
    return ' '.join(word.capitalize() for word in name.split())

def _validate_name(name: str, field_name: str = "nombre") -> str:
    """
    Valida que un nombre o apellido cumpla con los requisitos.
    
    Reglas:
    - No puede estar vacío
    - Debe tener entre 2 y 30 caracteres
    - Solo puede contener letras y espacios
    
    Devuelve el nombre formateado correctamente.
    """
    # Validar que no esté vacío
    if not name or not name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El {field_name} no puede estar vacío"
        )
    
    name = name.strip()
    
    # Validar longitud mínima y máxima
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El {field_name} debe tener al menos 2 caracteres"
        )
    
    max_length = 30
    if len(name) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"El {field_name} es demasiado largo",
                "details": {
                    "max_length": max_length,
                    "current_length": len(name),
                    "field": field_name
                }
            }
        )
    
    # Validar que solo contenga letras y espacios
    if not name.replace(' ', '').isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"El {field_name} solo puede contener letras y espacios",
                "details": {
                    "field": field_name,
                    "value": name,
                    "reason": "solo_se_permiten_letras_y_espacios"
                }
            }
        )
    
    # Formatear el nombre correctamente (primera letra de cada palabra en mayúscula)
    return _format_name(name)

# ==================== FUNCIONES PRINCIPALES ====================

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    
    # Preparar los datos a actualizar
    update_values = {}
    
    # Validar y actualizar nombre
    if update_data.first_name is not None:
        update_values['first_name'] = _validate_name(update_data.first_name, "nombre")
    
    # Validar y actualizar apellido
    if update_data.last_name is not None:
        update_values['last_name'] = _validate_name(update_data.last_name, "apellido")
    
    # Si no hay nada que actualizar, retornar el usuario actual
    if not update_values:
        return user
    
    try:
        # Actualizar los datos del usuario
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**update_values)
        )
        
        await db.execute(stmt)
        await db.commit()
        await db.refresh(user)
        return user
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el usuario: {str(e)}"
        )


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
