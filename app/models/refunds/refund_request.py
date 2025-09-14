from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime

class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_booking_id = Column(Integer, ForeignKey("payment_bookings.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    confirmation_id = Column(Integer, ForeignKey("confirmations.id"), nullable=False)
    
    # Detalles del refund
    refund_amount = Column(Float, nullable=False)  # Monto a reembolsar
    refund_type = Column(String(50), nullable=False)  # "before_class", "teacher_no_show"
    reason = Column(Text, nullable=True)  # Razón del refund
    
    # Estado del refund
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected, processed
    stripe_refund_id = Column(String(255), nullable=True)  # ID del refund en Stripe
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)  # Cuando se procesó el refund
    
    # Relaciones
    student = relationship("User", foreign_keys=[student_id], backref="refund_requests")
    payment_booking = relationship("PaymentBooking", backref="refund_requests")
    booking = relationship("Booking", backref="refund_requests")
    confirmation = relationship("Confirmation", backref="refund_requests")

    def __repr__(self):
        return f"<RefundRequest(id={self.id}, student_id={self.student_id}, amount={self.refund_amount}, status={self.status})>"
