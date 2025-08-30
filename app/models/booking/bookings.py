from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from app.models.subscriptions.plan import Plan

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    availability_id = Column(Integer, ForeignKey("availabilities.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    class_space = Column(String(100), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    availability = relationship("Availability", backref="bookings")
    user = relationship("User", backref="bookings")
    status = relationship("Status", backref="bookings")
    reschedule_requests = relationship("RescheduleRequest", back_populates="booking")

    def __repr__(self):
        return f"<PaymentBooking(availability_id={self.availability_id}, user_id={self.user_id}, status_id={self.status_id}, class_space={self.class_space})>"