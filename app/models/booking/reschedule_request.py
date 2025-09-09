from sqlalchemy import Column, Integer, DateTime, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from app.cores.db import Base
from datetime import datetime

class RescheduleRequest(Base):
    __tablename__ = "reschedule_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Horario actual
    current_availability_id = Column(Integer, ForeignKey("availabilities.id"), nullable=False)
    current_start_time = Column(DateTime, nullable=False)
    current_end_time = Column(DateTime, nullable=False)
    
    # Nuevo horario propuesto
    new_availability_id = Column(Integer, ForeignKey("availabilities.id"), nullable=False)
    new_start_time = Column(DateTime, nullable=False)
    new_end_time = Column(DateTime, nullable=False)
    
    # Motivo del cambio
    reason = Column(Text, nullable=True)
    
    # Estado de la solicitud
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=True)
    status = Column(String(20), default="pending")  # Fallback para compatibilidad
    
    # Respuesta del estudiante
    student_response = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)  # La solicitud expira después de cierto tiempo
    
    # Relaciones
    booking = relationship("Booking", back_populates="reschedule_requests")
    teacher = relationship("User", foreign_keys=[teacher_id])
    student = relationship("User", foreign_keys=[student_id])
    current_availability = relationship("Availability", foreign_keys=[current_availability_id])
    new_availability = relationship("Availability", foreign_keys=[new_availability_id])
    status_rel = relationship("Status", foreign_keys=[status_id])
