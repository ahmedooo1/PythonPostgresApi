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
from .models import ChildAssistance, ChildAssistanceStatus
from .schemas import ChildAssistanceCreate, ChildAssistanceResponse, ChildAssistanceUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ORDER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Child Assistance Service API",
    description="API for managing child assistance services in the platform",
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
            # Check if this is a child assistance order
            if order_data["service_type"] != "garde enfant":
                return None
                
            return order_data
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order service unavailable",
            )

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=ChildAssistanceResponse, status_code=status.HTTP_201_CREATED)
async def create_child_assistance(
    child_assistance: ChildAssistanceCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    # Validate that the order exists and is a child assistance order
    order = await validate_order(child_assistance.order_id, authorization)
    if not order:
        raise BadRequestException(detail=f"Order with ID {child_assistance.order_id} not found or is not a child assistance order")
    
    # Check if child assistance already exists for this order
    existing_assistance = db.query(ChildAssistance).filter(ChildAssistance.order_id == child_assistance.order_id).first()
    if existing_assistance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Child assistance already exists for order {child_assistance.order_id}"
        )
    
    db_assistance = ChildAssistance(
        order_id=child_assistance.order_id,
        guardian_name=child_assistance.guardian_name,
        child_count=child_assistance.child_count,
        destination=child_assistance.destination,
        status=ChildAssistanceStatus.IN_PROGRESS
    )
    
    db.add(db_assistance)
    db.commit()
    db.refresh(db_assistance)
    return db_assistance

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[ChildAssistanceResponse])
async def get_child_assistances(
    skip: int = 0, 
    limit: int = 100, 
    order_id: Optional[int] = None,
    status: Optional[ChildAssistanceStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    query = db.query(ChildAssistance)
    
    # Filter by order_id
    if order_id:
        # Validate that the user has access to this order
        order = await validate_order(order_id, authorization)
        if not order:
            # Return empty list if order doesn't exist or user doesn't have access
            return []
        
        query = query.filter(ChildAssistance.order_id == order_id)
    
    # Apply status filter
    if status:
        query = query.filter(ChildAssistance.status == status)
    
    assistances = query.offset(skip).limit(limit).all()
    
    # If user is not a provider, filter to only show those for their orders
    if current_user["role"] != "prestataire":
        filtered_assistances = []
        for assistance in assistances:
            order = await validate_order(assistance.order_id, authorization)
            if order and order["user_id"] == current_user["id"]:
                filtered_assistances.append(assistance)
        return filtered_assistances
    
    return assistances

@app.get(f"{API_PREFIX}/{API_VERSION}/{{assistance_id}}", response_model=ChildAssistanceResponse)
async def get_child_assistance(
    assistance_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    assistance = db.query(ChildAssistance).filter(ChildAssistance.id == assistance_id).first()
    
    if assistance is None:
        raise NotFoundException(detail=f"Child assistance with ID {assistance_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(assistance.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this child assistance record"
        )
    
    # Only allow viewing if order belongs to the user or user is a provider
    if current_user["role"] != "prestataire" and order["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this child assistance record"
        )
    
    return assistance

@app.put(f"{API_PREFIX}/{API_VERSION}/{{assistance_id}}", response_model=ChildAssistanceResponse)
async def update_child_assistance(
    assistance_id: int, 
    assistance_update: ChildAssistanceUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role),
    authorization: Optional[str] = Header(None)
):
    db_assistance = db.query(ChildAssistance).filter(ChildAssistance.id == assistance_id).first()
    
    if db_assistance is None:
        raise NotFoundException(detail=f"Child assistance with ID {assistance_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(db_assistance.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this child assistance record"
        )
    
    update_data = assistance_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_assistance, key, value)
    
    db.commit()
    db.refresh(db_assistance)
    return db_assistance

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "child-assistance-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
