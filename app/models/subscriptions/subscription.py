from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from datetime import datetime

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    payment_suscription_id = Column(Integer, ForeignKey("payment_subscriptions.id"), nullable=True)
    start_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="subscriptions")
    plan = relationship("Plan", backref="subscriptions")
    status = relationship("Status", backref="subscriptions")
    payment_subscription = relationship("PaymentSubscription", backref="subscriptions")

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan_id={self.plan_id}, status_id={self.status_id}, start_date={self.start_date}, end_date={self.end_date})>"