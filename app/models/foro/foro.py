from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.cores.db import Base

class Foro(Base):
    __tablename__ = "foro"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    category = relationship("Category", back_populates="foros")
    comments = relationship("ForoComment", back_populates="foro")

    def __repr__(self):
        return f"<Foro(id={self.id}, title={self.title}, user_id={self.user_id})>"
