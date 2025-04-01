from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from .database import Base
import enum

class ChildAssistanceStatus(str, enum.Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class ChildAssistance(Base):
    __tablename__ = "child_assistances"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)  # Reference to OrderService.id
    guardian_name = Column(String(100), nullable=False)
    child_count = Column(Integer, nullable=False)
    destination = Column(String(255), nullable=False)
    status = Column(Enum(ChildAssistanceStatus), default=ChildAssistanceStatus.IN_PROGRESS)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"ChildAssistance(id={self.id}, order_id={self.order_id}, guardian_name={self.guardian_name}, status={self.status})"
