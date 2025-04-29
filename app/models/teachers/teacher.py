from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.cores.db import Base
from sqlalchemy.sql import func


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    users_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    statuses_id = Column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", backref="teachers")
    statuses = relationship("Status", backref="teachers")

    def __repr__(self):
        return f"<Teacher(user_id={self.users_id})>"
