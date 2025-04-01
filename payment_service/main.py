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
from .models import Payment, PaymentStatus
from .schemas import PaymentCreate, PaymentResponse, PaymentUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ORDER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Payment Service API",
    description="API for managing payments in the services platform",
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
            
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order service unavailable",
            )

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    # Validate that the order exists and user has access to it
    order = await validate_order(payment.order_id, authorization)
    if not order:
        raise BadRequestException(detail=f"Order with ID {payment.order_id} not found or you don't have access to it")
    
    # Only allow creating payment if order belongs to the user or user is a provider
    if order["user_id"] != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a payment for this order"
        )
    
    # Check if payment already exists for this order
    existing_payment = db.query(Payment).filter(Payment.order_id == payment.order_id).first()
    if existing_payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment already exists for order {payment.order_id}"
        )
    
    db_payment = Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        payment_status=PaymentStatus.PENDING
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[PaymentResponse])
async def get_payments(
    skip: int = 0, 
    limit: int = 100, 
    order_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    query = db.query(Payment)
    
    # Filter by order_id
    if order_id:
        # Validate that the user has access to this order
        order = await validate_order(order_id, authorization)
        if not order:
            raise BadRequestException(detail=f"Order with ID {order_id} not found or you don't have access to it")
        
        query = query.filter(Payment.order_id == order_id)
    
    # Apply status filter
    if status:
        query = query.filter(Payment.payment_status == status)
    
    payments = query.offset(skip).limit(limit).all()
    
    # For non-providers, filter the payments to only show ones for their orders
    if current_user["role"] != "prestataire":
        filtered_payments = []
        for payment in payments:
            order = await validate_order(payment.order_id, authorization)
            if order and order["user_id"] == current_user["id"]:
                filtered_payments.append(payment)
        return filtered_payments
    
    return payments

@app.get(f"{API_PREFIX}/{API_VERSION}/{{payment_id}}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if payment is None:
        raise NotFoundException(detail=f"Payment with ID {payment_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(payment.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this payment"
        )
    
    # Only allow viewing payment if order belongs to the user or user is a provider
    if order["user_id"] != current_user["id"] and current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this payment"
        )
    
    return payment

@app.put(f"{API_PREFIX}/{API_VERSION}/{{payment_id}}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int, 
    payment_update: PaymentUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if db_payment is None:
        raise NotFoundException(detail=f"Payment with ID {payment_id} not found")
    
    # Validate that the user has access to the related order
    order = await validate_order(db_payment.order_id, authorization)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this payment"
        )
    
    # Only providers can update payment status
    if current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service providers can update payment status"
        )
    
    update_data = payment_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    db.commit()
    db.refresh(db_payment)
    return db_payment

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
