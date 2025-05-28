from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func
from datetime import datetime

class PrivilegeUser(Base):
    __tablename__ = "privilege_users"

    id = Column(Integer, primary_key=True, index=True)
    privilege_id = Column(Integer, ForeignKey("privileges.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    privilege = relationship("Privilege", backref="privilege_users")
    user = relationship("User", backref="privilege_users")
    status = relationship("Status", backref="privilege_users")

    def __repr__(self):
        return f"<PrivilegeUser(privilege_id={self.privilege_id}, user_id={self.user_id}, status_id={self.status_id})>"