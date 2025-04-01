from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey, func
from .database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to UserService.id
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Notification(id={self.id}, user_id={self.user_id}, is_read={self.is_read})"
