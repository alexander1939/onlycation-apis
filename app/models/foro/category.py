from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.cores.db import Base

class Category(Base):
    __tablename__ = "category"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relación con foro
    foros = relationship("Foro", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"
