from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ChildAssistanceStatus(str, Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class ChildAssistanceBase(BaseModel):
    order_id: int = Field(..., description="Order ID associated with this child assistance")
    guardian_name: str = Field(..., min_length=2, max_length=100, description="Name of the guardian")
    child_count: int = Field(..., gt=0, description="Number of children under care")
    destination: str = Field(..., min_length=2, max_length=255, description="Destination for the children")

class ChildAssistanceCreate(ChildAssistanceBase):
    pass

class ChildAssistanceUpdate(BaseModel):
    guardian_name: Optional[str] = Field(None, min_length=2, max_length=100)
    child_count: Optional[int] = Field(None, gt=0)
    destination: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[ChildAssistanceStatus] = None
    
    class Config:
        arbitrary_types_allowed = True

class ChildAssistanceResponse(ChildAssistanceBase):
    id: int
    status: ChildAssistanceStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
