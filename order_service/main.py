import sys
import os
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import jwt

# Add the parent directory to sys.path to import from shared package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.exceptions import NotFoundException, BadRequestException

from database import engine, get_db, Base
from .models import Order, ServiceType, OrderStatus
from .schemas import OrderCreate, OrderResponse, OrderUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Order Service API",
    description="API for managing orders in the services platform",
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

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Verify that user_id in request matches authenticated user
    if order.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create orders for your own account"
        )
    
    db_order = Order(
        user_id=order.user_id,
        service_type=order.service_type,
        latitude=order.latitude,
        longitude=order.longitude,
        status=OrderStatus.IN_PROGRESS
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0, 
    limit: int = 100, 
    user_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    service_type: Optional[ServiceType] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Order)
    
    # Filter by user_id
    if user_id:
        # Only allow seeing other users' orders for providers
        if user_id != current_user["id"] and current_user["role"] != "prestataire":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own orders"
            )
        query = query.filter(Order.user_id == user_id)
    elif current_user["role"] != "prestataire":
        # Non-providers can only see their own orders by default
        query = query.filter(Order.user_id == current_user["id"])
    
    # Apply other filters
    if status:
        query = query.filter(Order.status == status)
    if service_type:
        query = query.filter(Order.service_type == service_type)
    
    orders = query.offset(skip).limit(limit).all()
    return orders

@app.get(f"{API_PREFIX}/{API_VERSION}/{{order_id}}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order is None:
        raise NotFoundException(detail=f"Order with ID {order_id} not found")
    
    # Only allow viewing order if it belongs to the user or user is a provider
    if order.user_id != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this order"
        )
    
    return order

@app.put(f"{API_PREFIX}/{API_VERSION}/{{order_id}}", response_model=OrderResponse)
async def update_order(
    order_id: int, 
    order_update: OrderUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    
    if db_order is None:
        raise NotFoundException(detail=f"Order with ID {order_id} not found")
    
    # Only allow updating order if it belongs to the user or user is a provider
    if db_order.user_id != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this order"
        )
    
    update_data = order_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_order, key, value)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@app.delete(f"{API_PREFIX}/{API_VERSION}/{{order_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    
    if db_order is None:
        raise NotFoundException(detail=f"Order with ID {order_id} not found")
    
    # Only allow deleting an order if it belongs to the user or user is a provider
    if db_order.user_id != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this order"
        )
    
    db.delete(db_order)
    db.commit()
    return None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
