from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    guy = Column(String(100), nullable=False) 
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Integer, nullable=False)
    duration = Column(String(50), nullable=True)
    benefit_id= Column(Integer, ForeignKey("benefits.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    status = relationship("Status", backref="plans")
    benefit = relationship("Benefit", backref="plans")

    def __repr__(self):
        return f"<Plan(name={self.name}, description={self.description}, status_id={self.status_id})>"