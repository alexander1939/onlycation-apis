from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric
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
    
    # Campos para sistema de comisiones
    commission_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)  # % de comisión (5.00 o 0.00)
    commission_amount = Column(Integer, nullable=False, default=0)  # Cantidad de comisión en centavos
    teacher_amount = Column(Integer, nullable=False, default=0)  # Cantidad para el docente
    platform_amount = Column(Integer, nullable=False, default=0)  # Cantidad para la plataforma
    
    # Campos para transferencias diferidas
    transfer_date = Column(DateTime(timezone=True), nullable=True)  # Fecha de transferencia (booking + 15 días)
    transfer_status = Column(String(50), nullable=False, default="pending")  # pending, transferred, failed
    
    # Campos para Stripe Connect
    teacher_stripe_account_id = Column(String(100), nullable=True)  # Cuenta Stripe del docente
    stripe_transfer_id = Column(String(100), nullable=True)  # ID de transferencia de Stripe
    application_fee_amount = Column(Integer, nullable=True)  # Comisión en Stripe
    
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