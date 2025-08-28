from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime,String
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(Integer, ForeignKey("preferences.id"), nullable=False)
    price_range_id = Column(Integer, ForeignKey("price_ranges.id"), nullable=False)
    selected_prices = Column(Float, nullable=False)
    extra_hour_price = Column(Float, nullable=False)

    selected_prices = Column(Float, nullable=False)
    stripe_product_id = Column(String(100), nullable=True)
    stripe_price_id = Column(String(100), nullable=True)

    extra_hour_price = Column(Float, nullable=False)
    stripe_extra_product_id = Column(String(100), nullable=True)
    stripe_extra_price_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="teacher_prices")
    preference = relationship("Preference", backref="teacher_prices")
    price_range = relationship("PriceRange", backref="teacher_prices")

    def __repr__(self):
        return f"<TeacherPrice(id={self.id}, teacher_id={self.user_id})>"
