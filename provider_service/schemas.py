from pydantic import BaseModel, Field, EmailStr, confloat
from typing import Optional
from datetime import datetime

class ProviderBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Provider's name")
    email: EmailStr = Field(..., description="Provider's email address")
    availability: bool = Field(True, description="Provider's availability status")
    latitude: confloat(ge=-90, le=90) = Field(..., description="Provider's current latitude")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Provider's current longitude")

class ProviderCreate(ProviderBase):
    pass

class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    availability: Optional[bool] = None
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    
    class Config:
        arbitrary_types_allowed = True

class ProviderResponse(ProviderBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class ProviderLocationUpdate(BaseModel):
    latitude: confloat(ge=-90, le=90) = Field(..., description="Provider's current latitude")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Provider's current longitude")
