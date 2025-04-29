from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.sql import func
from app.cores.db import Base
from sqlalchemy.orm import relationship


class Preference(Base):
    __tablename__ = "preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    users_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    educational_levels_id = Column(Integer, ForeignKey("educational_levels.id"), nullable=False, index=True)
    modalities_id = Column(Integer, ForeignKey("modalities.id"), nullable=False, index=True)
    location=Column(String(100), index=True)
    location_description= Column(String(200),index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", backref="preferences")
    modalities = relationship("Modality", backref="preferences")
    educational_levels = relationship("EducationalLevel", backref="preferences")


    def __repr__(self):
        return f"<Preference(users_id={self.users_id},{self.educational_levels_id},{self.modalities_id},{self.location},{self.location_description})>"