from sqlalchemy import Column, Integer, String
from app.core.db import Base

class Status(Base):
    __tablename__ = "status"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, nullable=False, index=True)