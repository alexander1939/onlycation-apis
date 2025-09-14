from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import logging
from typing import Dict, Any

# Importar el filtro de contenido mejorado
from app.services.foro.content_filter import content_filter
from app.models.foro import ForoComment, Foro
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.foro.foro_comment_schema import (
    ForoCommentCreateRequest,
    ForoCommentUpdateMeRequest,
    ForoCommentDeleteMeRequest,
)
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


async def _validate_foro_exists(db: AsyncSession, foro_id: int):
    result = await db.execute(select(Foro).where(Foro.id == foro_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Foro con ID {foro_id} no encontrado")


async def _validate_comment_exists(db: AsyncSession, comment_id: int):
    result = await db.execute(select(ForoComment).where(ForoComment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail=f"Comentario con ID {comment_id} no encontrado")
    return comment


def _validate_comment_length(comment: str, min_length: int = 1, max_length: int = 1000):
    if not comment or not comment.strip():
        raise HTTPException(status_code=400, detail="El comentario no puede estar vacío")

    comment_length = len(comment.strip())
    if comment_length < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"El comentario debe tener al menos {min_length} caracteres",
        )
    if comment_length > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"El comentario no puede tener más de {max_length} caracteres",
        )


async def get_user_comment(
    db: AsyncSession, user_id: int, comment_id: int | None = None, foro_id: int | None = None
) -> ForoComment:
    query = select(ForoComment).where(ForoComment.user_id == user_id)

    if comment_id:
        await _validate_comment_exists(db, comment_id)
        query = query.where(ForoComment.id == comment_id)
    elif foro_id:
        await _validate_foro_exists(db, foro_id)
        query = query.where(ForoComment.foro_id == foro_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar foro_comment_id o foro_id",
        )

    result = await db.execute(query)
    comments = result.scalars().all()
    if not comments:
        raise HTTPException(
            status_code=404, detail="No se encontraron comentarios para este usuario"
        )

    return max(comments, key=lambda x: x.created_at)  # más reciente


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
# Create Comment
# -----------------------------
@handle_db_errors
async def create_foro_comment(db: AsyncSession, token: str, comment_data: ForoCommentCreateRequest) -> ForoComment:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)
    await _validate_foro_exists(db, comment_data.foro_id)

    comment_text = (comment_data.comment or "").strip()
    _validate_comment_length(comment_text, min_length=1, max_length=1000)

    # 🔴 Validación de contenido
    logging.info(f"Validando comentario para foro {comment_data.foro_id}: '{comment_text}'")
    content_filter.validate_content(comment_text, "comentario")

    db_comment = ForoComment(user_id=user_id, foro_id=comment_data.foro_id, comment=comment_text)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)

    logging.info(f"Comentario creado exitosamente con ID: {db_comment.id}")
    return db_comment


# -----------------------------
# Update My Comment
# -----------------------------
@handle_db_errors
async def update_my_foro_comment(db: AsyncSession, token: str, update_data: ForoCommentUpdateMeRequest) -> ForoComment:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)

    comment_text = (update_data.comment or "").strip()
    _validate_comment_length(comment_text, min_length=1, max_length=1000)
    logging.info(f"Validando comentario actualizado: '{comment_text}'")
    content_filter.validate_content(comment_text, "comentario")

    comment = await get_user_comment(
        db, user_id, comment_id=update_data.foro_comment_id, foro_id=update_data.foro_id
    )

    old_comment = comment.comment
    comment.comment = comment_text

    await db.commit()
    await db.refresh(comment)

    logging.info(f"Comentario actualizado - ID: {comment.id} ('{old_comment}' -> '{comment_text}')")
    return comment


# -----------------------------
# Delete My Comment
# -----------------------------
@handle_db_errors
async def delete_my_foro_comment(db: AsyncSession, token: str, delete_data: ForoCommentDeleteMeRequest) -> dict:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)

    comment = await get_user_comment(
        db, user_id, comment_id=delete_data.foro_comment_id, foro_id=delete_data.foro_id
    )

    comment_id = comment.id
    comment_text = comment.comment[:50] + "..." if len(comment.comment) > 50 else comment.comment

    await db.delete(comment)
    await db.commit()

    logging.info(f"Comentario eliminado - ID: {comment_id} ('{comment_text}')")
    return {"message": "Comentario eliminado exitosamente", "deleted_comment_id": comment_id}


async def get_my_comments(
    db: AsyncSession,
    token: str,
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene solo los comentarios del usuario autenticado"""
    payload = verify_token(token)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=ForoComment,
        offset=offset,
        limit=limit,
        filters={"user_id": user_id}
    )

async def get_recent_comments(
    db: AsyncSession,
    token: str,  # ← Agregar token
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene los comentarios más recientes"""
    payload = verify_token(token)
    if not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=ForoComment,
        offset=offset,
        limit=limit,
        filters=None
    )