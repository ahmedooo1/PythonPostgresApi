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

from .database import engine, get_db, Base
from .models import Repair, IssueType, RepairStatus
from .schemas import RepairCreate, RepairResponse, RepairUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ORDER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Repair Service API",
    description="API for managing repair services in the platform",
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
            # Check if this is a repair order
            if order_data["service_type"] != "dépannage":
                return None
                
            return order_data
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order service unavailable",
            )

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=RepairResponse, status_code=status.HTTP_201_CREATED)
async def create_repair(
    repair: RepairCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    # Validate that the order exists and is a repair order
    order = await validate_order(repair.order_id, authorization)
    if not order:
        raise BadRequestException(detail=f"Order with ID {repair.order_id} not found or is not a repair order")
    
    # Check if repair already exists for this order
    existing_repair = db.query(Repair).filter(Repair.order_id == repair.order_id).first()
    if existing_repair:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repair already exists for order {repair.order_id}"
        )
    
    db_repair = Repair(
        order_id=repair.order_id,
        issue_type=repair.issue_type,
        technician_name=repair.technician_name,
        status=RepairStatus.ON_THE_WAY
    )
    
    db.add(db_repair)
    db.commit()
    db.refresh(db_repair)
    return db_repair

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[RepairResponse])
async def get_repairs(
    skip: int = 0, 
    limit: int = 100, 
    order_id: Optional[int] = None,
    status: Optional[RepairStatus] = None,
    issue_type: Optional[IssueType] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    query = db.query(Repair)
    
    # Filter by order_id
    if order_id:
        # Validate that the user has access to this order
        order = await validate_order(order_id, authorization)
        if not order:
            # Return empty list if order doesn't exist or user doesn't have access
            return []
        
        query = query.filter(Repair.order_id == order_id)
    
    # Apply other filters
    if status:
        query = query.filter(Repair.status == status)
    if issue_type:
        query = query.filter(Repair.issue_type == issue_type)
    
    repairs = query.offset(skip).limit(limit).all()
    
    # If user is not a provider, filter repairs to only show those for their orders
    if current_user["role"] != "prestataire":
        filtered_repairs = []
        for repair in repairs:
            order = await validate_order(repair.order_id, authorization)
            if order and order["user_id"] == current_user["id"]:
                filtered_repairs.append(repair)
        return filtered_repairs
    
    return repairs

@app.get(f"{API_PREFIX}/{API_VERSION}/{{repair_id}}", response_model=RepairResponse)
async def get_repair(
    repair_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    
    if repair is None:
        raise NotFoundException(detail=f"Repair with ID {repair_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(repair.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this repair"
        )
    
    # Only allow viewing repair if order belongs to the user or user is a provider
    if current_user["role"] != "prestataire" and order["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this repair"
        )
    
    return repair

@app.put(f"{API_PREFIX}/{API_VERSION}/{{repair_id}}", response_model=RepairResponse)
async def update_repair(
    repair_id: int, 
    repair_update: RepairUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    db_repair = db.query(Repair).filter(Repair.id == repair_id).first()
    
    if db_repair is None:
        raise NotFoundException(detail=f"Repair with ID {repair_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(db_repair.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this repair"
        )
    
    update_data = repair_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_repair, key, value)
    
    db.commit()
    db.refresh(db_repair)
    return db_repair

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "repair-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
