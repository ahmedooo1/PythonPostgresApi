from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class TruckSize(str, Enum):
    SMALL = "petit"
    MEDIUM = "moyen"
    LARGE = "grand"

class MovingStatus(str, Enum):
    PREPARATION = "préparation"
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class MovingBase(BaseModel):
    order_id: int = Field(..., description="Order ID associated with this moving service")
    team_size: int = Field(..., gt=0, description="Number of movers in the team")
    truck_size: TruckSize = Field(..., description="Size of truck needed for moving")

class MovingCreate(MovingBase):
    pass

class MovingUpdate(BaseModel):
    team_size: Optional[int] = Field(None, gt=0)
    truck_size: Optional[TruckSize] = None
    status: Optional[MovingStatus] = None
    
    class Config:
        arbitrary_types_allowed = True

class MovingResponse(MovingBase):
    id: int
    status: MovingStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
