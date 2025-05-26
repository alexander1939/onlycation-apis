from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.cores.db import Base

class PriceRange(Base):
    __tablename__ = "price_ranges"
    
    id = Column(Integer, primary_key=True, index=True)
    educational_level_id = Column(Integer, ForeignKey("educational_levels.id"), nullable=False, index=True)
    minimum_price = Column(Float, nullable=False)
    maximum_price = Column(Float, nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    educational_level = relationship("EducationalLevel", backref="price_ranges")
    status = relationship("Status", backref="price_ranges")  


    def __repr__(self):
        return f"<PriceRange(name={self.minimum_price}{self.maximum_price})>"