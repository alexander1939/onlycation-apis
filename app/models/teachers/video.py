from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.cores.db import Base
from sqlalchemy.sql import func

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # YouTube video data
    youtube_video_id = Column(String(20), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    embed_url = Column(Text, nullable=False)
    privacy_status = Column(String(20), nullable=False)
    embeddable = Column(Boolean, nullable=False, default=True)
    original_url = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="teacher_videos")
    
    # Constraint: Un usuario solo puede tener un video
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_video'),
    )

    def __repr__(self):
        return f"<Video(id={self.id}, youtube_id={self.youtube_video_id})>"
