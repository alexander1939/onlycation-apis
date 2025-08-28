from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func
from datetime import datetime

class User_notification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="user_notifications")
    notification = relationship("Notification", backref="user_notifications")


    def __repr__(self):
        return f"<UserNotification(notification_id={self.notification_id}, is_read={self.is_read}, sent_at={self.sent_at})>"