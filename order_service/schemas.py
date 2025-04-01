from pydantic import BaseModel, Field, validator, confloat
from typing import Optional
from datetime import datetime
from enum import Enum

class ServiceType(str, Enum):
    TRANSPORT = "transport"
    CLEANING = "nettoyage"
    REPAIR = "dépannage"
    CHILD_ASSISTANCE = "garde enfant"
    MOVING = "déménagement"

class OrderStatus(str, Enum):
    IN_PROGRESS = "en cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"

class OrderBase(BaseModel):
    user_id: int = Field(..., description="User ID who placed the order")
    service_type: ServiceType = Field(..., description="Type of service requested")
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude of service location")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude of service location")

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    
    class Config:
        arbitrary_types_allowed = True

class OrderResponse(OrderBase):
    id: int
    status: OrderStatus
    created_at: datetime
    
    class Config:
        orm_mode = True
