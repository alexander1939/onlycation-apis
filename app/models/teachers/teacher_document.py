from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.cores.db import Base

class TeacherDocument(Base):
    __tablename__ = "teacher_documents"

    id = Column(Integer, primary_key=True, index=True)
    teachers_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    rfc = Column(String(13), nullable=False, unique=True, index=True)
    certificate = Column(String(255), nullable=False)
    curriculum = Column(String(255), nullable=False)
    expertise_area = Column(String(100), nullable=False) 

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    teachers = relationship("Teacher", backref="teacher_documents")


    def __repr__(self):
        return f"<Preference(users_id={self.teachers_id},{self.rfc},{self.certificate}{self.curriculum},{self.expertise_area})>"