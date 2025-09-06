from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc, func

from app.models.chat import Chat, Message
from app.models.users.user import User
from app.schemas.chat.chat_schema import MessageCreateRequest


class MessageService:
    """Servicio para la gestión de mensajes en el chat"""
    
    @staticmethod
    async def send_message(
        db: AsyncSession,
        chat_id: int,
        sender_id: int,
        content: str
    ) -> Message:
        """
        Envía un nuevo mensaje en un chat.
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            sender_id: ID del remitente
            content: Contenido del mensaje
            
        Returns:
            Message: El mensaje enviado
            
        Raises:
            ValueError: Si el chat no existe, está bloqueado, o el usuario no es participante
        """
        # Verificar que el chat existe y está activo
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat no encontrado")
        
        if not chat.is_active:
            raise ValueError("Este chat no está activo")
        
        if chat.is_blocked:
            raise ValueError("Este chat está bloqueado")
        
        # Verificar que el remitente es participante del chat
        if chat.student_id != sender_id and chat.teacher_id != sender_id:
            raise ValueError("No eres participante de este chat")
        
        # Crear y enviar el mensaje
        new_message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            is_read=False,
            is_deleted=False
        )
        
        db.add(new_message)
        
        # Actualizar timestamp del chat
        chat.updated_at = func.now()
        
        await db.commit()
        await db.refresh(new_message)
        
        return new_message
    
    @staticmethod
    async def get_chat_messages(
        db: AsyncSession,
        chat_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Obtiene los mensajes de un chat con paginación.
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            user_id: ID del usuario que solicita los mensajes
            limit: Número máximo de mensajes a retornar
            offset: Número de mensajes a omitir
            
        Returns:
            List[Message]: Lista de mensajes del chat
            
        Raises:
            ValueError: Si el chat no existe o el usuario no es participante
        """
        # Verificar que el chat existe
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat no encontrado")
        
        # Verificar que el usuario es participante del chat
        if chat.student_id != user_id and chat.teacher_id != user_id:
            raise ValueError("No eres participante de este chat")
        
        # Obtener mensajes con paginación
        query = select(Message).where(
            and_(
                Message.chat_id == chat_id,
                Message.is_deleted == False
            )
        ).order_by(desc(Message.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Retornar en orden cronológico (más antiguos primero)
        return list(reversed(messages))
    
    @staticmethod
    async def mark_messages_as_read(
        db: AsyncSession,
        chat_id: int,
        user_id: int,
        message_ids: List[int]
    ) -> int:
        """
        Marca mensajes como leídos.
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            user_id: ID del usuario que marca como leído
            message_ids: Lista de IDs de mensajes a marcar
            
        Returns:
            int: Número de mensajes marcados como leídos
            
        Raises:
            ValueError: Si el chat no existe o el usuario no es participante
        """
        # Verificar que el chat existe
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat no encontrado")
        
        # Verificar que el usuario es participante del chat
        if chat.student_id != user_id and chat.teacher_id != user_id:
            raise ValueError("No eres participante de este chat")
        
        # Marcar mensajes como leídos (solo los que no son del usuario)
        query = select(Message).where(
            and_(
                Message.id.in_(message_ids),
                Message.chat_id == chat_id,
                Message.sender_id != user_id,  # Solo mensajes de otros
                Message.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Marcar como leído
        for message in messages:
            message.is_read = True
        
        await db.commit()
        
        return len(messages)
    
    @staticmethod
    async def delete_message(
        db: AsyncSession,
        message_id: int,
        user_id: int
    ) -> bool:
        """
        Marca un mensaje como eliminado (soft delete).
        
        Args:
            db: Sesión de base de datos
            message_id: ID del mensaje
            user_id: ID del usuario que elimina el mensaje
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            ValueError: Si el mensaje no existe o el usuario no es el remitente
        """
        # Obtener el mensaje
        message = await db.get(Message, message_id)
        if not message:
            raise ValueError("Mensaje no encontrado")
        
        # Verificar que el usuario es el remitente del mensaje
        if message.sender_id != user_id:
            raise ValueError("Solo puedes eliminar tus propios mensajes")
        
        # Marcar como eliminado (soft delete)
        message.is_deleted = True
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        chat_id: int,
        user_id: int
    ) -> int:
        """
        Obtiene el número de mensajes no leídos en un chat.
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            user_id: ID del usuario
            
        Returns:
            int: Número de mensajes no leídos
        """
        query = select(func.count(Message.id)).where(
            and_(
                Message.chat_id == chat_id,
                Message.sender_id != user_id,  # Solo mensajes de otros
                Message.is_read == False,
                Message.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        return result.scalar() or 0
