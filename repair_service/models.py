from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from .database import Base
import enum

class IssueType(str, enum.Enum):
    BATTERY = "batterie"
    TIRE = "pneu"
    ENGINE = "moteur"
    OTHER = "autre"

class RepairStatus(str, enum.Enum):
    ON_THE_WAY = "en route"
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class Repair(Base):
    __tablename__ = "repairs"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)  # Reference to OrderService.id
    issue_type = Column(Enum(IssueType), nullable=False)
    technician_name = Column(String(100), nullable=False)
    status = Column(Enum(RepairStatus), default=RepairStatus.ON_THE_WAY)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Repair(id={self.id}, order_id={self.order_id}, issue_type={self.issue_type}, status={self.status})"
