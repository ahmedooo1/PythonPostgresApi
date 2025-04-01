from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, ForeignKey, func
from .database import Base
import enum

class ServiceType(str, enum.Enum):
    TRANSPORT = "transport"
    CLEANING = "nettoyage"
    REPAIR = "dépannage"
    CHILD_ASSISTANCE = "garde enfant"
    MOVING = "déménagement"

class OrderStatus(str, enum.Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to UserService.id
    service_type = Column(Enum(ServiceType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.IN_PROGRESS)
    latitude = Column(Float(precision=9), nullable=False)
    longitude = Column(Float(precision=9), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Order(id={self.id}, user_id={self.user_id}, service_type={self.service_type}, status={self.status})"
