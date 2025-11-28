from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, desc, func

from datetime import datetime, timezone

from app.models.chat import Chat, Message
from app.models.users.user import User
from app.models.users.profile import Profile
from app.schemas.chat.chat_schema import ChatCreateRequest, ChatSummaryResponse, MessageResponse, ParticipantResponse
from app.services.chat.message_service import MessageService
from app.models.booking.bookings import Booking
from app.models.teachers.availability import Availability
from app.models.common.status import Status


class ChatService:
    """Servicio para la gestión de chats entre estudiantes y profesores"""
    
    @staticmethod
    async def create_chat(
        db: AsyncSession, 
        student_id: int, 
        teacher_id: int
    ) -> Chat:
        """
        Crea (o recupera) un chat entre un estudiante y un profesor.
        - Reglas:
          * Solo se permite crear si existe una reserva ACTIVA (futura y no cancelada) entre ambos.
          * Si ya existe un chat ACTIVO entre estos usuarios, se devuelve ese chat (no se lanza error).
          * Si existe un chat inactivo, se reactiva.
        """
        
        # Regla de negocio: debe existir al menos una reserva futura no cancelada entre ambos
        has_active = await ChatService.has_active_booking_between(db, student_id, teacher_id)
        if not has_active:
            raise ValueError("Solo puedes chatear si tienes una reserva activa con este profesor")

        # Buscar chat existente entre estos usuarios
        existing_chat = await ChatService.get_chat_between_users(db, student_id, teacher_id)
        
        if existing_chat and existing_chat.is_active:
            # Devolver el existente activo
            return existing_chat
        
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
    async def _get_user_participant_info(
        db: AsyncSession,
        user_id: int
    ) -> Optional[dict]:
        """Obtiene la información del participante (usuario)"""
        try:
            # Obtener el usuario con su perfil en una sola consulta
            stmt = select(
                User,
                Profile
            ).outerjoin(
                Profile, User.id == Profile.user_id
            ).where(User.id == user_id)
            
            result = await db.execute(stmt)
            user_data = result.first()
            
            if not user_data or not user_data[0]:  # Si no hay usuario
                return None
                
            user = user_data[0]
            profile = user_data[1]  # Puede ser None si no hay perfil
            
            return {
                "id": user.id,
                "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip()
            }
            
        except Exception as e:
            print(f"Error al obtener información del participante {user_id}: {str(e)}")
            return None
    
    @staticmethod
    async def get_chat_summaries(
        db: AsyncSession, 
        user_id: int, 
        user_role: str
    ) -> List[ChatSummaryResponse]:
        """
        Obtiene resúmenes de chats con información del último mensaje y contador de no leídos.
        Incluye información del participante (estudiante o profesor según el rol del usuario actual).
        """
        # Obtener chats del usuario
        chats = await ChatService.get_user_chats(db, user_id, user_role)
        summaries = []
        
        for chat in chats:
            # Determinar el ID del otro participante
            # Si el usuario actual es estudiante, el participante es el profesor y viceversa
            other_participant_id = chat.teacher_id if user_role == "student" else chat.student_id
            
            # Obtener información del otro participante
            participant_info = await ChatService._get_user_participant_info(db, other_participant_id)
            
            # Si no se pudo obtener la información del participante, saltar este chat
            if not participant_info:
                continue
                
            # Obtener último mensaje
            last_message_query = select(Message).where(
                and_(
                    Message.chat_id == chat.id,
                    Message.is_deleted == False
                )
            ).order_by(desc(Message.created_at)).limit(1)
            
            last_message_result = await db.execute(last_message_query)
            last_message = last_message_result.scalar_one_or_none()
            
            # Procesar último mensaje si existe
            last_message_response = None
            if last_message:
                try:
                    decrypted_content = MessageService.decrypt_message_content(last_message, user_id)
                    last_message_response = MessageResponse(
                        id=last_message.id,
                        chat_id=last_message.chat_id,
                        sender_id=last_message.sender_id,
                        content=decrypted_content,
                        is_read=last_message.is_read,
                        is_deleted=last_message.is_deleted,
                        is_encrypted=last_message.is_encrypted,
                        encryption_version=last_message.encryption_version,
                        created_at=last_message.created_at,
                        updated_at=last_message.updated_at
                    )
                except Exception as e:
                    last_message_response = None
            
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
            
            # Crear resumen con la información del participante
            summary = ChatSummaryResponse(
                chat_id=chat.id,
                student_id=chat.student_id,
                teacher_id=chat.teacher_id,
                participant=ParticipantResponse(**participant_info),
                last_message=last_message_response,
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
    
    @staticmethod
    async def has_active_booking_between(
        db: AsyncSession,
        student_id: int,
        teacher_id: int,
    ) -> bool:
        """
        Verifica si existe una reserva ACTIVA (futura y no cancelada) entre el alumno y el docente.
        - Futura: Booking.start_time > ahora (UTC)
        - No cancelada: Booking.status != 'cancelled' (si existe el status)
        """
        # Buscar status cancelado (si existe)
        cancelled = (await db.execute(select(Status).where(Status.name == "cancelled"))).scalar_one_or_none()
        cancelled_id = cancelled.id if cancelled else None

        now_utc = datetime.now(timezone.utc)

        # Count de reservas que cumplan las condiciones
        q = (
            select(func.count(Booking.id))
            .join(Availability, Booking.availability_id == Availability.id)
            .where(
                Booking.user_id == student_id,
                Availability.user_id == teacher_id,
                Booking.start_time > now_utc,
            )
        )
        if cancelled_id is not None:
            q = q.where(Booking.status_id != cancelled_id)

        total = (await db.execute(q)).scalar() or 0
        return total > 0

    @staticmethod
    async def ensure_chats_for_user_active_bookings(
        db: AsyncSession,
        user_id: int,
    ) -> None:
        """Asegura (crea o reactiva) chats para TODAS las reservas activas del usuario.
        "Reserva activa": Booking.start_time > ahora y Booking.status != 'cancelled' (si existe el status).
        - Si el usuario es alumno en la reserva -> asegura chat (student=user_id, teacher=availability.user_id)
        - Si el usuario es docente en la reserva -> asegura chat (student=booking.user_id, teacher=user_id)
        Idempotente: si el chat ya existe activo, no hace nada; si existe inactivo, lo reactiva.
        """
        # Buscar status cancelado (si existe)
        cancelled = (await db.execute(select(Status).where(Status.name == "cancelled"))).scalar_one_or_none()
        cancelled_id = cancelled.id if cancelled else None

        now_utc = datetime.now(timezone.utc)

        # Consultar reservas activas donde el usuario participa como alumno o docente
        q = (
            select(Booking, Availability.user_id.label("teacher_id"))
            .join(Availability, Booking.availability_id == Availability.id)
            .where(
                Booking.start_time > now_utc,
                or_(
                    Booking.user_id == user_id,          # alumno
                    Availability.user_id == user_id       # docente
                )
            )
        )
        if cancelled_id is not None:
            q = q.where(Booking.status_id != cancelled_id)

        result = await db.execute(q)
        rows = result.all()

        pairs = set()
        for row in rows:
            booking: Booking = row[0]
            teacher_id: int = row[1]
            # Determinar rol del usuario en esta reserva
            if booking.user_id == user_id:
                # usuario es alumno
                student_id = user_id
                tid = teacher_id
            else:
                # usuario es docente
                student_id = booking.user_id
                tid = user_id

            if not student_id or not tid:
                continue

            key = (student_id, tid)
            if key in pairs:
                continue
            pairs.add(key)

            # Asegurar chat (crea/retorna/reactiva)
            try:
                await ChatService.create_chat(db=db, student_id=student_id, teacher_id=tid)
            except Exception:
                # Continuar con el resto aunque uno falle
                continue