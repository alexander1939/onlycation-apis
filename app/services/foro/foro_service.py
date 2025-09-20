from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import logging
from typing import Dict, Any


# Asegúrate de importar tu filtro mejorado
from app.services.foro.content_filter import content_filter
from app.models.foro import Foro, Category
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.foro.foro_schema import ForoCreateRequest, ForoUpdateMeRequest
from app.services.utils.pagination_service import PaginationService  


# -----------------------------
# Helpers
# -----------------------------
async def get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido: falta user_id")
    return user_id


async def _validate_user_exists(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"El usuario con ID {user_id} no existe")


async def _validate_category_exists(db: AsyncSession, category_id: int):
    result = await db.execute(select(Category).where(Category.id == category_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"La categoría con ID {category_id} no existe")


def _validate_text_length(text: str, field_name: str, min_length: int = 3, max_length: int = 500):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail=f"El {field_name} no puede estar vacío")

    text_length = len(text.strip())
    if text_length < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"El {field_name} debe tener al menos {min_length} caracteres",
        )
    if text_length > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"El {field_name} no puede tener más de {max_length} caracteres",
        )


def handle_db_errors(func):
    """Decorador para capturar errores y simplificar manejo de excepciones"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error en {func.__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    return wrapper


# -----------------------------
# Create Foro
# -----------------------------
@handle_db_errors
async def create_foro(db: AsyncSession, token: str, foro_data: ForoCreateRequest) -> Foro:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)
    await _validate_category_exists(db, foro_data.category_id)

    title = (foro_data.title or "").strip()
    description = (foro_data.description or "").strip()

    _validate_text_length(title, "título", min_length=3, max_length=200)
    _validate_text_length(description, "descripción", min_length=10, max_length=1000)

    # 🔴 Validación de contenido
    logging.info(f"Validando contenido - Título: '{title}', Descripción: '{description}'")
    content_filter.validate_content(title, "título")
    content_filter.validate_content(description, "descripción")

    db_foro = Foro(
        user_id=user_id,
        category_id=foro_data.category_id,
        title=title,
        description=description,
    )

    db.add(db_foro)
    await db.commit()
    await db.refresh(db_foro)

    logging.info(f"Foro creado exitosamente con ID: {db_foro.id}")
    return db_foro


# -----------------------------
# Update My Foro
# -----------------------------
@handle_db_errors
async def update_my_foro(db: AsyncSession, token: str, update_data: ForoUpdateMeRequest) -> Foro:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)

    result = await db.execute(
        select(Foro).where(Foro.id == update_data.foro_id, Foro.user_id == user_id)
    )
    foro = result.scalar_one_or_none()

    if not foro:
        raise HTTPException(status_code=404, detail="Foro no encontrado o no pertenece al usuario")

    update_values = update_data.model_dump(exclude_unset=True, exclude={"foro_id"})

    if "category_id" in update_values:
        await _validate_category_exists(db, update_values["category_id"])

    if "title" in update_values:
        title = update_values["title"].strip()
        _validate_text_length(title, "título", min_length=3, max_length=200)
        logging.info(f"Validando título actualizado: '{title}'")
        content_filter.validate_content(title, "título")
        update_values["title"] = title

    if "description" in update_values:
        description = update_values["description"].strip()
        _validate_text_length(description, "descripción", min_length=10, max_length=1000)
        logging.info(f"Validando descripción actualizada: '{description}'")
        content_filter.validate_content(description, "descripción")
        update_values["description"] = description

    for field, value in update_values.items():
        setattr(foro, field, value)

    await db.commit()
    await db.refresh(foro)

    logging.info(f"Foro actualizado exitosamente - ID: {foro.id}")
    return foro



async def get_my_foros(
    db: AsyncSession,
    token: str,
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene solo los foros del usuario autenticado"""
    payload = verify_token(token)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=Foro,
        offset=offset,
        limit=limit,
        filters={"user_id": user_id}
    )

async def get_recent_foros(
    db: AsyncSession,
    token: str,  # ← AGREGAR token aquí también
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene los foros más recientes (ordenados por fecha)"""
    # Solo validamos el token, no usamos el user_id para filtro
    payload = verify_token(token)
    if not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=Foro,
        offset=offset,
        limit=limit,
        filters=None
    )