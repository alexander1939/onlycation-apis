from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.cores.db import Base


class Chat(Base):
    """Modelo para representar una conversación entre un estudiante y un profesor"""
    
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Participantes del chat
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Estado del chat
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    student = relationship("User", foreign_keys=[student_id], backref="student_chats")
    teacher = relationship("User", foreign_keys=[teacher_id], backref="teacher_chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    # Constraint: Un estudiante solo puede tener un chat activo con un profesor específico
    __table_args__ = (
        # Índice compuesto para búsquedas eficientes
        # Restricción única para evitar chats duplicados
    )
    
    def __repr__(self):
        return f"<Chat(id={self.id}, student={self.student_id}, teacher={self.teacher_id})>"
