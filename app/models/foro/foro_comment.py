from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.cores.db import Base

class ForoComment(Base):
    __tablename__ = "foro_comment"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    foro_id = Column(Integer, ForeignKey("foro.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    foro = relationship("Foro", back_populates="comments")
    replies = relationship(
        "ForoReplyComment",
        back_populates="comment_parent",
        passive_deletes=True  # 🔑 evita cascadas indeseadas
    )

    def __repr__(self):
        return f"<ForoComment(id={self.id}, foro_id={self.foro_id}, user_id={self.user_id})>"
