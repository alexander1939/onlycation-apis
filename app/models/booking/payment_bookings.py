from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from app.models.booking.bookings import Booking

class PaymentBooking(Base):
    __tablename__ = "payment_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    price_id = Column(Integer, ForeignKey("prices.id"), nullable=False)
    total_amount = Column(Integer, nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    stripe_payment_intent_id = Column(String(100), nullable=True)  
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="payment_bookings")
    price = relationship("Price", backref="payment_bookings")
    booking = relationship("Booking", backref="payment_bookings") 
    status = relationship("Status", backref="payment_bookings")

    def __repr__(self):
        return f"<PaymentBooking(booking_id={self.booking_id}, user_id={self.user_id}, status_id={self.status_id})>"