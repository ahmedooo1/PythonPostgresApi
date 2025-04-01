from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, func
from .database import Base
import enum

class TruckSize(str, enum.Enum):
    SMALL = "petit"
    MEDIUM = "moyen"
    LARGE = "grand"

class MovingStatus(str, enum.Enum):
    PREPARATION = "préparation"
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class Moving(Base):
    __tablename__ = "movings"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)  # Reference to OrderService.id
    team_size = Column(Integer, nullable=False)
    truck_size = Column(Enum(TruckSize), nullable=False)
    status = Column(Enum(MovingStatus), default=MovingStatus.PREPARATION)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Moving(id={self.id}, order_id={self.order_id}, team_size={self.team_size}, truck_size={self.truck_size}, status={self.status})"
