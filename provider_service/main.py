import sys
import os
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

# Add the parent directory to sys.path to import from shared package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.exceptions import NotFoundException, BadRequestException, ConflictException

from database import engine, get_db, Base
from .models import Provider
from .schemas import ProviderCreate, ProviderResponse, ProviderUpdate, ProviderLocationUpdate
from .config import SERVICE_HOST, SERVICE_PORT, API_PREFIX, API_VERSION, USER_SERVICE_URL, ALLOWED_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="Provider Service API",
    description="API for managing service providers in the platform",
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

# Provider access check
async def check_provider_role(current_user = Depends(get_current_user)):
    if current_user["role"] != "prestataire":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service providers can access this resource"
        )
    return current_user

# Routes
@app.post(f"{API_PREFIX}/{API_VERSION}/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider: ProviderCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(check_provider_role)
):
    # Check if provider with this email already exists
    db_provider = db.query(Provider).filter(Provider.email == provider.email).first()
    if db_provider:
        raise ConflictException(detail="Provider with this email already exists")
    
    db_provider = Provider(
        name=provider.name,
        email=provider.email,
        availability=provider.availability,
        latitude=provider.latitude,
        longitude=provider.longitude
    )
    
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider

@app.get(f"{API_PREFIX}/{API_VERSION}/", response_model=List[ProviderResponse])
async def get_providers(
    skip: int = 0, 
    limit: int = 100, 
    available_only: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Provider)
    
    if available_only:
        query = query.filter(Provider.availability == True)
    
    providers = query.offset(skip).limit(limit).all()
    return providers

@app.get(f"{API_PREFIX}/{API_VERSION}/{{provider_id}}", response_model=ProviderResponse)
async def get_provider(
    provider_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    
    if provider is None:
        raise NotFoundException(detail=f"Provider with ID {provider_id} not found")
    
    return provider

@app.put(f"{API_PREFIX}/{API_VERSION}/{{provider_id}}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int, 
    provider_update: ProviderUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role)
):
    db_provider = db.query(Provider).filter(Provider.id == provider_id).first()
    
    if db_provider is None:
        raise NotFoundException(detail=f"Provider with ID {provider_id} not found")
    
    # Check if the user is trying to update their own provider record
    # Assuming email uniquely identifies a provider corresponding to a user
    if db_provider.email != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own provider profile"
        )
    
    # Check if trying to update email to one that already exists
    if provider_update.email and provider_update.email != db_provider.email:
        existing_email = db.query(Provider).filter(Provider.email == provider_update.email).first()
        if existing_email:
            raise ConflictException(detail="Provider with this email already exists")
    
    update_data = provider_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_provider, key, value)
    
    db.commit()
    db.refresh(db_provider)
    return db_provider

@app.put(f"{API_PREFIX}/{API_VERSION}/{{provider_id}}/location", response_model=ProviderResponse)
async def update_provider_location(
    provider_id: int, 
    location_update: ProviderLocationUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role)
):
    db_provider = db.query(Provider).filter(Provider.id == provider_id).first()
    
    if db_provider is None:
        raise NotFoundException(detail=f"Provider with ID {provider_id} not found")
    
    # Check if the user is trying to update their own provider record
    if db_provider.email != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own provider location"
        )
    
    db_provider.latitude = location_update.latitude
    db_provider.longitude = location_update.longitude
    
    db.commit()
    db.refresh(db_provider)
    return db_provider

@app.put(f"{API_PREFIX}/{API_VERSION}/{{provider_id}}/availability", response_model=ProviderResponse)
async def toggle_availability(
    provider_id: int, 
    available: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(check_provider_role)
):
    db_provider = db.query(Provider).filter(Provider.id == provider_id).first()
    
    if db_provider is None:
        raise NotFoundException(detail=f"Provider with ID {provider_id} not found")
    
    # Check if the user is trying to update their own provider record
    if db_provider.email != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own availability"
        )
    
    db_provider.availability = available
    
    db.commit()
    db.refresh(db_provider)
    return db_provider

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "provider-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
