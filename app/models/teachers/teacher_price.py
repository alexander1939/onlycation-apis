from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func

class TeacherPrice(Base):
    __tablename__ = "teacher_prices"

    id = Column(Integer, primary_key=True, index=True)
    teachers_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    preferences_id = Column(Integer, ForeignKey("preferences.id"), nullable=False)
    price_ranges_id = Column(Integer, ForeignKey("price_ranges.id"), nullable=False)
    selected_prices = Column(Float, nullable=False)
    extra_hour_price = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    teachers = relationship("Teacher", backref="teacher_prices")
    preferences = relationship("Preference", backref="teacher_prices")
    price_ranges = relationship("PriceRange", backref="teacher_prices")

    def __repr__(self):
        return f"<TeacherPrice(id={self.id}, teacher_id={self.teacher_id})>"
