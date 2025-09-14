from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import logging
from typing import Dict, Any

# Importar el filtro de contenido mejorado
from app.services.foro.content_filter import content_filter
from app.models.foro import ForoReplyComment, ForoComment
from app.models.users.user import User
from app.cores.token import verify_token
from app.schemas.foro.foro_reply_comment_schema import (
    ForoReplyCommentCreateRequest,
    ForoReplyCommentUpdateMeRequest,
    ForoReplyCommentDeleteMeRequest,
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


async def _validate_comment_exists(db: AsyncSession, comment_id: int):
    result = await db.execute(select(ForoComment).where(ForoComment.id == comment_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Comentario con ID {comment_id} no encontrado")


async def _validate_reply_comment_exists(db: AsyncSession, reply_comment_id: int):
    result = await db.execute(select(ForoReplyComment).where(ForoReplyComment.id == reply_comment_id))
    reply_comment = result.scalar_one_or_none()
    if not reply_comment:
        raise HTTPException(status_code=404, detail=f"Respuesta de comentario con ID {reply_comment_id} no encontrada")
    return reply_comment


def _validate_reply_length(reply: str, min_length: int = 1, max_length: int = 500):
    if not reply or not reply.strip():
        raise HTTPException(status_code=400, detail="La respuesta no puede estar vacía")

    reply_length = len(reply.strip())
    if reply_length < min_length:
        raise HTTPException(status_code=400, detail=f"La respuesta debe tener al menos {min_length} caracteres")
    if reply_length > max_length:
        raise HTTPException(status_code=400, detail=f"La respuesta no puede tener más de {max_length} caracteres")


async def validate_user_and_comment(
    db: AsyncSession, user_id: int, comment_id: int | None = None, reply_id: int | None = None
):
    await _validate_user_exists(db, user_id)
    if comment_id:
        await _validate_comment_exists(db, comment_id)
    if reply_id:
        return await _validate_reply_comment_exists(db, reply_id)


async def get_user_reply(
    db: AsyncSession, user_id: int, reply_id: int | None = None, comment_id: int | None = None
) -> ForoReplyComment:
    query = select(ForoReplyComment).where(ForoReplyComment.user_id == user_id)

    if reply_id:
        await _validate_reply_comment_exists(db, reply_id)
        query = query.where(ForoReplyComment.id == reply_id)
    elif comment_id:
        await _validate_comment_exists(db, comment_id)
        query = query.where(ForoReplyComment.foro_comment_id == comment_id)
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar foro_reply_comment_id o foro_comment_id")

    result = await db.execute(query)
    replies = result.scalars().all()
    if not replies:
        raise HTTPException(status_code=404, detail="No se encontraron respuestas para este usuario")

    return max(replies, key=lambda x: x.created_at)  # más reciente


# Decorador para manejo de errores genérico
def handle_db_errors(func):
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
# Create Reply
# -----------------------------
@handle_db_errors
async def create_foro_reply_comment(
    db: AsyncSession, token: str, reply_data: ForoReplyCommentCreateRequest
) -> ForoReplyComment:
    user_id = await get_user_id_from_token(token)
    await validate_user_and_comment(db, user_id, comment_id=reply_data.foro_comment_id)

    reply_text = (reply_data.comment or "").strip()
    _validate_reply_length(reply_text)
    content_filter.validate_content(reply_text, "respuesta")

    db_reply = ForoReplyComment(
        user_id=user_id,
        foro_comment_id=reply_data.foro_comment_id,
        comment=reply_text,
    )

    db.add(db_reply)
    await db.commit()
    await db.refresh(db_reply)

    logging.info(f"Respuesta creada exitosamente con ID: {db_reply.id}")
    return db_reply


# -----------------------------
# Update My Reply
# -----------------------------
@handle_db_errors
async def update_my_foro_reply_comment(
    db: AsyncSession, token: str, update_data: ForoReplyCommentUpdateMeRequest
) -> ForoReplyComment:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)

    reply_text = (update_data.comment or "").strip()
    _validate_reply_length(reply_text)
    content_filter.validate_content(reply_text, "respuesta")

    reply = await get_user_reply(
        db, user_id, reply_id=update_data.foro_reply_comment_id, comment_id=update_data.foro_comment_id
    )

    old_reply = reply.comment
    reply.comment = reply_text

    await db.commit()
    await db.refresh(reply)

    logging.info(f"Respuesta actualizada - ID: {reply.id} ('{old_reply}' -> '{reply_text}')")
    return reply


# -----------------------------
# Delete My Reply
# -----------------------------
@handle_db_errors
async def delete_my_foro_reply_comment(
    db: AsyncSession, token: str, delete_data: ForoReplyCommentDeleteMeRequest
) -> dict:
    user_id = await get_user_id_from_token(token)
    await _validate_user_exists(db, user_id)

    reply = await get_user_reply(
        db, user_id, reply_id=delete_data.foro_reply_comment_id, comment_id=delete_data.foro_comment_id
    )

    reply_id = reply.id
    reply_text = reply.comment[:50] + "..." if len(reply.comment) > 50 else reply.comment

    await db.delete(reply)
    await db.commit()

    logging.info(f"Respuesta eliminada - ID: {reply_id} ('{reply_text}')")

    return {"message": "Respuesta eliminada exitosamente", "deleted_reply_id": reply_id}






async def get_my_replies(
    db: AsyncSession,
    token: str,
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene solo las respuestas del usuario autenticado"""
    payload = verify_token(token)
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=ForoReplyComment,
        offset=offset,
        limit=limit,
        filters={"user_id": user_id}
    )


async def get_recent_replies(
    db: AsyncSession,
    token: str, 
    offset: int = 0,
    limit: int = 6
) -> Dict[str, Any]:
    """Obtiene las respuestas más recientes"""
    payload = verify_token(token)
    if not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return await PaginationService.get_paginated_data(
        db=db,
        model=ForoReplyComment,
        offset=offset,
        limit=limit,
        filters=None
    )