from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from .database import Base
import enum

class CleaningStatus(str, enum.Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class CleaningType(str, enum.Enum):
    STANDARD = "standard"
    DEEP = "profond"
    SPECIALIZED = "spécialisé"

class Cleaning(Base):
    __tablename__ = "cleanings"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)  # Reference to OrderService.id
    cleaning_type = Column(Enum(CleaningType), nullable=False)
    cleaner_name = Column(String(100), nullable=False)
    estimated_duration = Column(Integer, nullable=False)  # In minutes
    status = Column(Enum(CleaningStatus), default=CleaningStatus.IN_PROGRESS)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Cleaning(id={self.id}, order_id={self.order_id}, type={self.cleaning_type}, status={self.status})"
