from sqlalchemy import Column, Integer, Enum, DateTime, Numeric, ForeignKey, func
from .database import Base
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "en attente"
    VALIDATED = "validé"
    FAILED = "échoué"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)  # Reference to OrderService.id
    amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Payment(id={self.id}, order_id={self.order_id}, amount={self.amount}, status={self.payment_status})"
