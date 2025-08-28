from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.cores.db import Base

class StripePrice(Base):
    __tablename__ = "stripe_prices"

    id = Column(Integer, primary_key=True, index=True)
    stripe_product_id = Column(String(100), nullable=True)
    stripe_price_id = Column(String(100), nullable=False, unique=True)  
    amount = Column(Float, nullable=False, index=True)  
    currency = Column(String(10), nullable=False, default="mxn")
    type = Column(String(50), nullable=False)  
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('amount', 'type', name='uix_amount_type'),
    )

    def __repr__(self):
        return f"<StripePrice(id={self.id}, amount={self.amount}, type='{self.type}')>"
