from pydantic import BaseModel, Field, condecimal
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "en attente"
    VALIDATED = "validé"
    FAILED = "échoué"

class PaymentBase(BaseModel):
    order_id: int = Field(..., description="Order ID associated with this payment")
    amount: condecimal(max_digits=10, decimal_places=2) = Field(..., gt=0, description="Payment amount")

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    payment_status: Optional[PaymentStatus] = None
    
    class Config:
        arbitrary_types_allowed = True

class PaymentResponse(PaymentBase):
    id: int
    payment_status: PaymentStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
