from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from sqlalchemy.sql import func


class Modality(Base):
    __tablename__ = "modalities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False, index=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    status = relationship("Status", backref="modalities")

    def __repr__(self):
        return f"<Modality(name={self.name})>"
