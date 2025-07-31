from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.cores.db import Base

class Profile(Base):
    __tablename__ = "profile"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    credential = Column(String(255), nullable=False)
    gender = Column(String(50), nullable=True)
    sex = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    
    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, credential={self.credential})>"