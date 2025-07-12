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
    # Eliminamos benefit_id ya que usaremos tabla intermedia
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    status = relationship("Status", backref="plans")
    # Relación muchos a muchos con Benefit a través de PlanBenefit
    benefits = relationship("Benefit", secondary="plan_benefits", back_populates="plans")
    role = relationship("Role", backref="plans")

    def __repr__(self):
        return f"<Plan(name={self.name}, description={self.description}, status_id={self.status_id})>"