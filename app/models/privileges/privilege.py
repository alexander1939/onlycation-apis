from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func
from datetime import datetime



class Privilege(Base):
    __tablename__ = "privileges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    action = Column(String(255), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    status = relationship("Status", backref="privileges")

    def __repr__(self):
        return f"<Privilege(name={self.name})>"
    