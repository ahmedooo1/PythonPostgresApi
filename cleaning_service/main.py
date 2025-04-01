import sys
import os
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

# Add the parent directory to sys.path to import from shared package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.exceptions import NotFoundException, BadRequestException

from database import engine, get_db, Base
from .models import Cleaning, CleaningType, CleaningStatus
from .schemas import CleaningCreate, CleaningResponse, CleaningUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ORDER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Cleaning Service API",
    description="API for managing cleaning services in the platform",
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

# Provider role check
async def check_provider_role(current_user = Depends(get_current_user)):
    if current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service providers can access this resource"
        )
    return current_user

# Helper function to validate order
async def validate_order(order_id: int, authorization: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ORDER_SERVICE_URL}/api/orders/v1/{order_id}",
                headers={"Authorization": authorization}
            )
            
            if response.status_code != 200:
                return None
            
            order_data = response.json()
            # Check if this is a cleaning order
            if order_data["service_type"] != "nettoyage":
                return None
                
            return order_data
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order service unavailable",
            )

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=CleaningResponse, status_code=status.HTTP_201_CREATED)
async def create_cleaning(
    cleaning: CleaningCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    # Validate that the order exists and is a cleaning order
    order = await validate_order(cleaning.order_id, authorization)
    if not order:
        raise BadRequestException(detail=f"Order with ID {cleaning.order_id} not found or is not a cleaning order")
    
    # Check if cleaning service already exists for this order
    existing_cleaning = db.query(Cleaning).filter(Cleaning.order_id == cleaning.order_id).first()
    if existing_cleaning:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cleaning service already exists for order {cleaning.order_id}"
        )
    
    db_cleaning = Cleaning(
        order_id=cleaning.order_id,
        cleaning_type=cleaning.cleaning_type,
        cleaner_name=cleaning.cleaner_name,
        estimated_duration=cleaning.estimated_duration,
        status=CleaningStatus.IN_PROGRESS
    )
    
    db.add(db_cleaning)
    db.commit()
    db.refresh(db_cleaning)
    return db_cleaning

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[CleaningResponse])
async def get_cleanings(
    skip: int = 0, 
    limit: int = 100, 
    order_id: Optional[int] = None,
    status: Optional[CleaningStatus] = None,
    cleaning_type: Optional[CleaningType] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    query = db.query(Cleaning)
    
    # Filter by order_id
    if order_id:
        # Validate that the user has access to this order
        order = await validate_order(order_id, authorization)
        if not order:
            # Return empty list if order doesn't exist or user doesn't have access
            return []
        
        query = query.filter(Cleaning.order_id == order_id)
    
    # Apply other filters
    if status:
        query = query.filter(Cleaning.status == status)
    if cleaning_type:
        query = query.filter(Cleaning.cleaning_type == cleaning_type)
    
    cleanings = query.offset(skip).limit(limit).all()
    
    # If user is not a provider, filter to only show those for their orders
    if current_user["role"] != "prestataire":
        filtered_cleanings = []
        for cleaning in cleanings:
            order = await validate_order(cleaning.order_id, authorization)
            if order and order["user_id"] == current_user["id"]:
                filtered_cleanings.append(cleaning)
        return filtered_cleanings
    
    return cleanings

@app.get(f"{API_PREFIX}/{API_VERSION}/{{cleaning_id}}", response_model=CleaningResponse)
async def get_cleaning(
    cleaning_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    cleaning = db.query(Cleaning).filter(Cleaning.id == cleaning_id).first()
    
    if cleaning is None:
        raise NotFoundException(detail=f"Cleaning with ID {cleaning_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(cleaning.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this cleaning service"
        )
    
    # Only allow viewing if order belongs to the user or user is a provider
    if current_user["role"] != "prestataire" and order["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this cleaning service"
        )
    
    return cleaning

@app.put(f"{API_PREFIX}/{API_VERSION}/{{cleaning_id}}", response_model=CleaningResponse)
async def update_cleaning(
    cleaning_id: int, 
    cleaning_update: CleaningUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    db_cleaning = db.query(Cleaning).filter(Cleaning.id == cleaning_id).first()
    
    if db_cleaning is None:
        raise NotFoundException(detail=f"Cleaning with ID {cleaning_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(db_cleaning.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this cleaning service"
        )
    
    update_data = cleaning_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_cleaning, key, value)
    
    db.commit()
    db.refresh(db_cleaning)
    return db_cleaning

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "cleaning-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
