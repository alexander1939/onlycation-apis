from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, String
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func

class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(Integer, ForeignKey("preferences.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="teacher_availabilities")
    preference = relationship("Preference", backref="teacher_availabilities")

    def __repr__(self):
        return f"<TeacherAvailability(id={self.id}, teacher_id={self.user_id})>"
