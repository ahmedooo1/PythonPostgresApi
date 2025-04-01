from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    user_id: int = Field(..., description="User ID who will receive this notification")
    message: str = Field(..., description="Notification message content")

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    
    class Config:
        arbitrary_types_allowed = True

class NotificationResponse(NotificationBase):
    id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        orm_mode = True
