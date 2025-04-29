from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from sqlalchemy.sql import func
from app.cores.db import Base

class Status(Base):
    __tablename__ = "statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    
    def __repr__(self):
        return f"<Status(name={self.name})>"
