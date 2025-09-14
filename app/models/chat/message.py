from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.cores.db import Base


class Message(Base):
    """Modelo para representar un mensaje individual en un chat"""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relaciones
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Contenido del mensaje (encriptado)
    encrypted_content = Column(Text, nullable=False)  # Contenido encriptado
    # content = Column(Text, nullable=True)  # ELIMINADO por seguridad - NO guardar contenido original
    
    # Información de encriptación
    encryption_version = Column(String(10), default="v1", nullable=False)  # Versión de encriptación
    is_encrypted = Column(Boolean, default=True, nullable=False)  # Indica si está encriptado
    
    # Estado del mensaje
    is_read = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", backref="sent_messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat={self.chat_id}, sender={self.sender_id}, encrypted={self.is_encrypted})>"
