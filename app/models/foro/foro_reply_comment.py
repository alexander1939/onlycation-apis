from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.cores.db import Base

class ForoReplyComment(Base):
    __tablename__ = "foro_reply_comment"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    foro_comment_id = Column(
        Integer,
        ForeignKey("foro_comment.id", ondelete="SET NULL"),  # 🔑
        nullable=True  # 🔑 permitir null
    )
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relación con comentario padre
    comment_parent = relationship("ForoComment", back_populates="replies")

    def __repr__(self):
        return f"<ForoReplyComment(id={self.id}, foro_comment_id={self.foro_comment_id}, user_id={self.user_id})>"
