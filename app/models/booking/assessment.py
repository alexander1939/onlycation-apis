from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from app.models.subscriptions.plan import Plan

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_booking_id = Column(Integer, ForeignKey("payment_bookings.id"), nullable=False)
    qualification = Column(Integer, nullable=True)
    comment = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


    user = relationship("User", backref="assessments")
    payment_booking = relationship("PaymentBooking", backref="assessments")

    def __repr__(self):
        return f"<Assessment(user_id={self.user_id}, payment_booking_id={self.payment_booking_id}, qualification={self.qualification}, comment={self.comment}, status_id={self.status_id})>"