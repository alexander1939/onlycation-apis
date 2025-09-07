from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, desc, func

from app.models.chat import Chat, Message
from app.models.users.user import User
from app.schemas.chat.chat_schema import ChatCreateRequest, ChatSummaryResponse


class ChatService:
    """Servicio para la gestión de chats entre estudiantes y profesores"""
    
    @staticmethod
    async def create_chat(
        db: AsyncSession, 
        student_id: int, 
        teacher_id: int
    ) -> Chat:
        """
        Crea un nuevo chat entre un estudiante y un profesor.
        
        Args:
            db: Sesión de base de datos
            student_id: ID del estudiante
            teacher_id: ID del profesor
            
        Returns:
            Chat: El chat creado
            
        Raises:
            ValueError: Si ya existe un chat activo entre estos usuarios
        """
        # Verificar que no exista un chat activo entre estos usuarios
        existing_chat = await ChatService.get_chat_between_users(
            db, student_id, teacher_id
        )
        
        if existing_chat and existing_chat.is_active:
            raise ValueError(
                f"Ya existe un chat activo entre el estudiante {student_id} y el profesor {teacher_id}"
            )
        
        # Si existe un chat inactivo, reactivarlo
        if existing_chat and not existing_chat.is_active:
            existing_chat.is_active = True
            existing_chat.is_blocked = False
            await db.commit()
            await db.refresh(existing_chat)
            return existing_chat
        
        # Crear nuevo chat
        new_chat = Chat(
            student_id=student_id,
            teacher_id=teacher_id,
            is_active=True,
            is_blocked=False
        )
        
        db.add(new_chat)
        await db.commit()
        await db.refresh(new_chat)
        
        return new_chat
    
    @staticmethod
    async def get_chat_between_users(
        db: AsyncSession, 
        student_id: int, 
        teacher_id: int
    ) -> Optional[Chat]:
        """
        Obtiene el chat existente entre un estudiante y un profesor.
        
        Args:
            db: Sesión de base de datos
            student_id: ID del estudiante
            teacher_id: ID del profesor
            
        Returns:
            Optional[Chat]: El chat si existe, None en caso contrario
        """
        query = select(Chat).where(
            and_(
                Chat.student_id == student_id,
                Chat.teacher_id == teacher_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_chats(
        db: AsyncSession, 
        user_id: int, 
        user_role: str
    ) -> List[Chat]:
        """
        Obtiene todos los chats de un usuario (estudiante o profesor).
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            user_role: Rol del usuario ('student' o 'teacher')
            
        Returns:
            List[Chat]: Lista de chats del usuario
        """
        if user_role == "student":
            query = select(Chat).where(
                and_(
                    Chat.student_id == user_id,
                    Chat.is_active == True
                )
            ).order_by(desc(Chat.updated_at))
        else:
            query = select(Chat).where(
                and_(
                    Chat.teacher_id == user_id,
                    Chat.is_active == True
                )
            ).order_by(desc(Chat.updated_at))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_chat_summaries(
        db: AsyncSession, 
        user_id: int, 
        user_role: str
    ) -> List[ChatSummaryResponse]:
        """
        Obtiene resúmenes de chats con información del último mensaje y contador de no leídos.
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            user_role: Rol del usuario ('student' o 'teacher')
            
        Returns:
            List[ChatSummaryResponse]: Lista de resúmenes de chats
        """
        # Obtener chats del usuario
        chats = await ChatService.get_user_chats(db, user_id, user_role)
        summaries = []
        
        for chat in chats:
            # Obtener último mensaje
            last_message_query = select(Message).where(
                and_(
                    Message.chat_id == chat.id,
                    Message.is_deleted == False
                )
            ).order_by(desc(Message.created_at)).limit(1)
            
            last_message_result = await db.execute(last_message_query)
            last_message = last_message_result.scalar_one_or_none()
            
            # Contar mensajes no leídos
            unread_query = select(func.count(Message.id)).where(
                and_(
                    Message.chat_id == chat.id,
                    Message.sender_id != user_id,
                    Message.is_read == False,
                    Message.is_deleted == False
                )
            )
            
            unread_result = await db.execute(unread_query)
            unread_count = unread_result.scalar() or 0
            
            # Crear resumen
            summary = ChatSummaryResponse(
                chat_id=chat.id,
                student_id=chat.student_id,
                teacher_id=chat.teacher_id,
                last_message=last_message,
                unread_count=unread_count,
                is_active=chat.is_active,
                created_at=chat.created_at,
                updated_at=chat.updated_at
            )
            
            summaries.append(summary)
        
        return summaries
    
    @staticmethod
    async def block_chat(
        db: AsyncSession, 
        chat_id: int, 
        user_id: int
    ) -> Chat:
        """
        Bloquea un chat (solo el propietario puede hacerlo).
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            user_id: ID del usuario que bloquea
            
        Returns:
            Chat: El chat bloqueado
            
        Raises:
            ValueError: Si el usuario no es propietario del chat
        """
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat no encontrado")
        
        # Verificar que el usuario sea propietario del chat
        if chat.student_id != user_id and chat.teacher_id != user_id:
            raise ValueError("No tienes permisos para bloquear este chat")
        
        chat.is_blocked = True
        await db.commit()
        await db.refresh(chat)
        
        return chat
    
    @staticmethod
    async def unblock_chat(
        db: AsyncSession, 
        chat_id: int, 
        user_id: int
    ) -> Chat:
        """
        Desbloquea un chat (solo el propietario puede hacerlo).
        
        Args:
            db: Sesión de base de datos
            chat_id: ID del chat
            user_id: ID del usuario que desbloquea
            
        Returns:
            Chat: El chat desbloqueado
            
        Raises:
            ValueError: Si el usuario no es propietario del chat
        """
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise ValueError("Chat no encontrado")
        
        # Verificar que el usuario sea propietario del chat
        if chat.student_id != user_id and chat.teacher_id != user_id:
            raise ValueError("No tienes permisos para desbloquear este chat")
        
        chat.is_blocked = False
        await db.commit()
        await db.refresh(chat)
        
        return chat
