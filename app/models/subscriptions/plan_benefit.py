from sqlalchemy import Column, Integer, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime

# Tabla intermedia para relación muchos a muchos entre Plan y Benefit
plan_benefits = Table(
    'plan_benefits',
    Base.metadata,
    Column('plan_id', Integer, ForeignKey('plans.id'), primary_key=True),
    Column('benefit_id', Integer, ForeignKey('benefits.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), default=datetime.utcnow, nullable=False)
) 