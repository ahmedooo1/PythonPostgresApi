import sys
import os
from fastapi import FastAPI, Depends, HTTPException, status, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

# Add the parent directory to sys.path to import from shared package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.exceptions import NotFoundException, BadRequestException

from database import engine, get_db, Base
from .models import Notification
from .schemas import NotificationCreate, NotificationResponse, NotificationUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Notification Service API",
    description="API for managing notifications in the services platform",
    version="1.0.0",
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_type, token = authorization.split()
    if token_type.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token with the user service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{USER_SERVICE_URL}/api/users/v1/me",
                headers={"Authorization": authorization}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User service unavailable",
            )

# Helper function to validate user exists
async def validate_user(user_id: int, authorization: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{USER_SERVICE_URL}/api/users/v1/{user_id}",
                headers={"Authorization": authorization}
            )
            
            if response.status_code != 200:
                return None
            
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User service unavailable",
            )

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification: NotificationCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    # Only providers can create notifications for other users
    if notification.user_id != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create notifications for other users"
        )
    
    # Validate that the user exists
    user = await validate_user(notification.user_id, authorization)
    if not user:
        raise BadRequestException(detail=f"User with ID {notification.user_id} not found")
    
    db_notification = Notification(
        user_id=notification.user_id,
        message=notification.message,
        is_read=False
    )
    
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = 0, 
    limit: int = 100, 
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.user_id == current_user["id"])
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return notifications

@app.get(f"{API_PREFIX}/{API_VERSION}/{{notification_id}}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    
    if notification is None:
        raise NotFoundException(detail=f"Notification with ID {notification_id} not found")
    
    # Only allow viewing notification if it belongs to the user or user is a provider
    if notification.user_id != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this notification"
        )
    
    return notification

@app.put(f"{API_PREFIX}/{API_VERSION}/{{notification_id}}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int, 
    notification_update: NotificationUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_notification = db.query(Notification).filter(Notification.id == notification_id).first()
    
    if db_notification is None:
        raise NotFoundException(detail=f"Notification with ID {notification_id} not found")
    
    # Only allow updating notification if it belongs to the user
    if db_notification.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this notification"
        )
    
    update_data = notification_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_notification, key, value)
    
    db.commit()
    db.refresh(db_notification)
    return db_notification

@app.put(f"{API_PREFIX}/{API_VERSION}/mark-all-read", response_model=dict)
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = db.query(Notification).filter(
        Notification.user_id == current_user["id"],
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    return {"success": True, "count": result}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notification-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
