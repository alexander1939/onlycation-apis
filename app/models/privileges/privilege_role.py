from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func
from datetime import datetime

class PrivilegeRole(Base):
    __tablename__ = "privilege_roles"

    id = Column(Integer, primary_key=True, index=True)
    privilege_id = Column(Integer, ForeignKey("privileges.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    privilege = relationship("Privilege", backref="privilege_roles")
    role = relationship("Role", backref="privilege_roles")
    status = relationship("Status", backref="privilege_roles")

    def __repr__(self):
        return f"<PrivilegeRole(privilege_id={self.privilege_id}, role_id={self.role_id}, status_id={self.status_id})>"