from sqlalchemy import Column, Integer, String, ForeignKey, DATETIME
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime



class Benefit(Base):
    __tablename__ = "benefits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DATETIME(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DATETIME(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    status = relationship("Status", backref="benefits")
    plans = relationship("Plan", secondary="plan_benefits", back_populates="benefits")

    def __repr__(self):
        return f"<Benefit(name={self.name}, description={self.description}, status_id={self.status_id})>"