from sqlalchemy import Column, Integer, String, ForeignKey, DateTime,Boolean
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from app.models.subscriptions.plan import Plan

class Confirmation(Base):
    __tablename__ = "confirmations"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_booking_id = Column(Integer, ForeignKey("payment_bookings.id"), nullable=False)
    confirmation_date_teacher = Column(Boolean, nullable=True, default=None)
    confirmation_date_student = Column(Boolean, nullable=True, default=None)
    evidence_student = Column(String(255), nullable=True)
    evidence_teacher = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    payment_booking = relationship("PaymentBooking", backref="confirmations")
    teacher = relationship("User", foreign_keys=[teacher_id], backref="teacher_confirmations")
    student = relationship("User", foreign_keys=[student_id], backref="student_confirmations")
    
    def __repr__(self):
        return f"<Confirmation(teacher_id={self.teacher_id}, student_id={self.student_id}, payment_booking_id={self.payment_booking_id}, confirmation_date_teacher={self.confirmation_date_teacher}, confirmation_date_student={self.confirmation_date_student}, evidence={self.evidence})>"