from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class CleaningStatus(str, Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class CleaningType(str, Enum):
    STANDARD = "standard"
    DEEP = "profond"
    SPECIALIZED = "spécialisé"

class CleaningBase(BaseModel):
    order_id: int = Field(..., description="Order ID associated with this cleaning service")
    cleaning_type: CleaningType = Field(..., description="Type of cleaning service")
    cleaner_name: str = Field(..., min_length=2, max_length=100, description="Name of the cleaner")
    estimated_duration: int = Field(..., gt=0, description="Estimated duration in minutes")

class CleaningCreate(CleaningBase):
    pass

class CleaningUpdate(BaseModel):
    cleaning_type: Optional[CleaningType] = None
    cleaner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    estimated_duration: Optional[int] = Field(None, gt=0)
    status: Optional[CleaningStatus] = None
    
    class Config:
        arbitrary_types_allowed = True

class CleaningResponse(CleaningBase):
    id: int
    status: CleaningStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
