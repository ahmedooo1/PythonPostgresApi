from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class IssueType(str, Enum):
    BATTERY = "batterie"
    TIRE = "pneu"
    ENGINE = "moteur"
    OTHER = "autre"

class RepairStatus(str, Enum):
    ON_THE_WAY = "en route"
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class RepairBase(BaseModel):
    order_id: int = Field(..., description="Order ID associated with this repair")
    issue_type: IssueType = Field(..., description="Type of issue to be repaired")
    technician_name: str = Field(..., min_length=2, max_length=100, description="Name of the technician")

class RepairCreate(RepairBase):
    pass

class RepairUpdate(BaseModel):
    issue_type: Optional[IssueType] = None
    technician_name: Optional[str] = Field(None, min_length=2, max_length=100)
    status: Optional[RepairStatus] = None
    
    class Config:
        arbitrary_types_allowed = True

class RepairResponse(RepairBase):
    id: int
    status: RepairStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
