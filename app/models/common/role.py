from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from sqlalchemy.sql import func


class Role(Base):
    __tablename__ = "roles"  

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), index=True)
    description = Column(String(50))
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    status = relationship("Status", backref="roles")  
    
    def __repr__(self):
        return f"<Role(name={self.name}, description={self.description})>"
