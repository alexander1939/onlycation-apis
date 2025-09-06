from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.apis.deps import get_db, auth_required
from app.schemas.chat.chat_schema import (
    ChatCreateRequest,
    ChatResponse,
    ChatListResponse,
    MessageCreateRequest,
    MessageResponse,
    MessageListResponse,
    MarkAsReadRequest,
    ChatSummaryResponse,
    ChatSummaryListResponse,
)
from app.services.chat import ChatService, MessageService

router = APIRouter()


# ============================================================================
# ENDPOINTS PARA CHATS
# ============================================================================

@router.post("/chats/create", response_model=ChatResponse)
async def create_chat(
    request: ChatCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Crea un nuevo chat entre un estudiante y un profesor.
    
    Solo los estudiantes pueden crear chats con profesores.
    """
    try:
        print(f"🔍 DEBUG: Usuario actual: {current_user}")
        print(f"🔍 DEBUG: Request: {request}")
        
        # Verificar que el usuario es estudiante
        if current_user["role"] != "student":
            print(f"❌ DEBUG: Usuario no es estudiante, rol: {current_user['role']}")
            raise HTTPException(
                status_code=403,
                detail="❌ Solo los estudiantes pueden crear chats con profesores"
            )
        
        print(f"✅ DEBUG: Usuario es estudiante")
        
        # Verificar que el estudiante no está creando un chat consigo mismo
        if current_user["user_id"] == request.teacher_id:
            print(f"❌ DEBUG: Estudiante intentando crear chat consigo mismo")
            raise HTTPException(
                status_code=400,
                detail="❌ No puedes crear un chat contigo mismo"
            )
        
        print(f"✅ DEBUG: Validaciones pasadas, creando chat...")
        
        # Crear el chat
        chat = await ChatService.create_chat(
            db=db,
            student_id=current_user["user_id"],
            teacher_id=request.teacher_id
        )
        
        print(f"✅ DEBUG: Chat creado exitosamente: {chat}")
        
        print(f"🔍 DEBUG: Validando ChatResponse...")
        try:
            response = ChatResponse.model_validate(chat)
            print(f"✅ DEBUG: ChatResponse validado exitosamente: {response}")
            return response
        except Exception as validation_error:
            print(f"❌ DEBUG: Error en ChatResponse.model_validate: {validation_error}")
            print(f"❌ DEBUG: Tipo de error: {type(validation_error)}")
            import traceback
            print(f"❌ DEBUG: Traceback de validación: {traceback.format_exc()}")
            raise
        
    except HTTPException:
        # Re-lanzar HTTPException sin modificar (403, 400, etc.)
        raise
    except ValueError as e:
        print(f"❌ DEBUG: ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        print(f"❌ DEBUG: Exception: {str(e)}")
        print(f"❌ DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al crear el chat. Por favor, intenta nuevamente."
        )


@router.get("/chats/my", response_model=ChatSummaryListResponse)
async def get_my_chats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Obtiene todos los chats del usuario autenticado con resúmenes.
    """
    try:
        summaries = await ChatService.get_chat_summaries(
            db=db,
            user_id=current_user["user_id"],
            user_role=current_user["role"]
        )
        
        return ChatSummaryListResponse(
            success=True,
            message=f"Se encontraron {len(summaries)} chat(s) en tu cuenta",
            data=summaries,
            total=len(summaries)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al obtener los chats. Por favor, intenta nuevamente."
        )


@router.post("/chats/{chat_id}/block")
async def block_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Bloquea un chat (solo el propietario puede hacerlo).
    """
    try:
        chat = await ChatService.block_chat(
            db=db,
            chat_id=chat_id,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "message": "✅ Chat bloqueado exitosamente",
            "data": ChatResponse.model_validate(chat)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al bloquear el chat. Por favor, intenta nuevamente."
        )


@router.post("/chats/{chat_id}/unblock")
async def unblock_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Desbloquea un chat (solo el propietario puede hacerlo).
    """
    try:
        chat = await ChatService.unblock_chat(
            db=db,
            chat_id=chat_id,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "message": "✅ Chat desbloqueado exitosamente",
            "data": ChatResponse.model_validate(chat)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al desbloquear el chat. Por favor, intenta nuevamente."
        )


# ============================================================================
# ENDPOINTS PARA MENSAJES
# ============================================================================

@router.post("/messages/send", response_model=MessageResponse)
async def send_message(
    request: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Envía un nuevo mensaje en un chat.
    """
    try:
        message = await MessageService.send_message(
            db=db,
            chat_id=request.chat_id,
            sender_id=current_user["user_id"],
            content=request.content
        )
        
        return MessageResponse.model_validate(message)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al enviar el mensaje. Por favor, intenta nuevamente."
        )


@router.get("/messages/{chat_id}", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: int,
    limit: int = Query(50, ge=1, le=100, description="Número máximo de mensajes"),
    offset: int = Query(0, ge=0, description="Número de mensajes a omitir"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Obtiene los mensajes de un chat con paginación.
    """
    try:
        messages = await MessageService.get_chat_messages(
            db=db,
            chat_id=chat_id,
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset
        )
        
        # Convertir a schema de respuesta
        message_responses = [MessageResponse.model_validate(msg) for msg in messages]
        
        return MessageListResponse(
            success=True,
            message=f"Se encontraron {len(message_responses)} mensaje(s) en el chat",
            data=message_responses,
            total=len(message_responses),
            chat_id=chat_id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al obtener los mensajes. Por favor, intenta nuevamente."
        )


@router.post("/messages/mark-read")
async def mark_messages_as_read(
    request: MarkAsReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Marca mensajes como leídos.
    """
    try:
        # Obtener el chat_id del primer mensaje (todos deben ser del mismo chat)
        if not request.message_ids:
            raise HTTPException(
                status_code=400,
                detail="❌ Debes proporcionar al menos un ID de mensaje"
            )
        
        # Obtener el primer mensaje para verificar el chat
        from app.models.chat import Message
        from sqlalchemy.future import select
        
        first_message_query = select(Message).where(Message.id == request.message_ids[0])
        first_message_result = await db.execute(first_message_query)
        first_message = first_message_result.scalar_one_or_none()
        
        if not first_message:
            raise HTTPException(status_code=404, detail="❌ Mensaje no encontrado")
        
        chat_id = first_message.chat_id
        
        # Marcar como leído
        count = await MessageService.mark_messages_as_read(
            db=db,
            chat_id=chat_id,
            user_id=current_user["user_id"],
            message_ids=request.message_ids
        )
        
        return {
            "success": True,
            "message": f"✅ {count} mensaje(s) marcado(s) como leído(s)",
            "data": {"marked_count": count}
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al marcar mensajes como leídos. Por favor, intenta nuevamente."
        )


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Elimina un mensaje (soft delete).
    """
    try:
        success = await MessageService.delete_message(
            db=db,
            message_id=message_id,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "message": "✅ Mensaje eliminado exitosamente",
            "data": {"deleted": success}
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"❌ {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al eliminar el mensaje. Por favor, intenta nuevamente."
        )


@router.get("/messages/{chat_id}/unread-count")
async def get_unread_count(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(auth_required)
):
    """
    Obtiene el número de mensajes no leídos en un chat.
    """
    try:
        count = await MessageService.get_unread_count(
            db=db,
            chat_id=chat_id,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "message": f"Tienes {count} mensaje(s) no leído(s)",
            "data": {"unread_count": count}
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="❌ Error interno al obtener el contador de mensajes no leídos. Por favor, intenta nuevamente."
        )
