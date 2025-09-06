from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.cores.db import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # NUEVO: hash para unicidad/búsqueda
    rfc_hash = Column(String(64), nullable=False, unique=True, index=True)

    # NUEVO: RFC cifrado (base64)
    rfc_cipher = Column(Text, nullable=False)

    # Rutas de archivos CIFRADOS (.enc)
    certificate = Column(String(255), nullable=False)
    curriculum = Column(String(255), nullable=False)

    expertise_area = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="teacher_documents")

    def __repr__(self):
        return f"<Document(user_id={self.user_id}, expertise_area={self.expertise_area})>"
