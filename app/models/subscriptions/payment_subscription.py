from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime
from app.models.subscriptions.plan import Plan

class PaymentSubscription(Base):
    __tablename__ = "payment_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_payment_intent_id = Column(String(100), nullable=True)  
    payment_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("Plan", backref="payment_subscriptions")
    user = relationship("User", backref="payment_subscriptions")
    status = relationship("Status", backref="payment_subscriptions")

    def __repr__(self):
        return f"<PaymentSubscription(plan_id={self.plan_id}, user_id={self.user_id}, status_id={self.status_id})>"