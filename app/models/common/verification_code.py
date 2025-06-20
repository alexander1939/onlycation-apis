from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.cores.db import Base

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    role = Column(String(50), nullable=True)
    purpose = Column(String(50), nullable=False)
    code = Column(String(6), nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<VerificationCode(email={self.email}, code={self.code}, used={self.used})>"
