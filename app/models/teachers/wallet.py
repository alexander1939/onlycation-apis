from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)  
    stripe_account_id = Column(String(50), nullable=True, unique=True) 
    stripe_bank_status = Column(String(50), nullable=True) 
    stripe_setup_url = Column(String(500), nullable=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="Wallet")

    def __repr__(self):
        return f"<Wallet(user_id={self.user_id}, stripe_account_id={self.stripe_account_id})>"
