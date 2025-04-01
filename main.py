from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import logging
import requests
from typing import Dict, Any, Optional, List
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://localhost:8000",
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
    "*"  # For development
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs - using environment variables with fallback to localhost
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004")
PROVIDER_SERVICE_URL = os.getenv("PROVIDER_SERVICE_URL", "http://localhost:8005")
REPAIR_SERVICE_URL = os.getenv("REPAIR_SERVICE_URL", "http://localhost:8006")
CHILD_ASSISTANCE_SERVICE_URL = os.getenv("CHILD_ASSISTANCE_SERVICE_URL", "http://localhost:8007")
MOVING_SERVICE_URL = os.getenv("MOVING_SERVICE_URL", "http://localhost:8008")
CLEANING_SERVICE_URL = os.getenv("CLEANING_SERVICE_URL", "http://localhost:8009")

# Service route mapping
SERVICE_ROUTES = {
    "/api/users": USER_SERVICE_URL,
    "/api/orders": ORDER_SERVICE_URL,
    "/api/payments": PAYMENT_SERVICE_URL,
    "/api/notifications": NOTIFICATION_SERVICE_URL,
    "/api/providers": PROVIDER_SERVICE_URL,
    "/api/repairs": REPAIR_SERVICE_URL,
    "/api/child-assistance": CHILD_ASSISTANCE_SERVICE_URL,
    "/api/moving": MOVING_SERVICE_URL,
    "/api/cleaning": CLEANING_SERVICE_URL,
}

def get_service_url(path: str) -> Optional[str]:
    """Determine which service to route to based on the path"""
    for route_prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(route_prefix):
            return service_url
    return None

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Service Platform API Gateway",
        "version": "1.0.0",
        "documentation": "/docs",
        "healthcheck": "/health"
    }

from pydantic import BaseModel

class ServiceInfo(BaseModel):
    name: str
    url: str
    health: str

class ApiDocsResponse(BaseModel):
    api_name: str
    version: str
    services: List[ServiceInfo]
    endpoints: Dict[str, str]

@app.get("/api-docs", response_model=None)
async def api_docs():
    """API Documentation"""
    services = []
    for route, url in SERVICE_ROUTES.items():
        services.append({
            "name": route.replace("/api/", ""),
            "url": route,
            "health": f"{route}/health"
        })
    
    return {
        "api_name": "Service Platform API",
        "version": "1.0.0",
        "services": services,
        "endpoints": {
            "root": "/",
            "health": "/health",
            "api_docs": "/api-docs"
        }
    }

@app.get("/health")
async def health_check():
    """Check the health of all services"""
    health_statuses = {}
    service_status = "healthy"  # Default status
    
    # Check health of all services
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICE_ROUTES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                if response.status_code == 200:
                    health_statuses[service_name] = "healthy"
                else:
                    health_statuses[service_name] = f"unhealthy (status: {response.status_code})"
                    service_status = "degraded"
            except Exception as e:
                health_statuses[service_name] = f"unavailable ({str(e)})"
                service_status = "degraded"
    
    return {
        "status": service_status,
        "service": "api-gateway",
        "services": health_statuses
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_endpoint(request: Request, path: str):
    """Generic endpoint that proxies requests to the appropriate service"""
    # Get the full path
    full_path = str(request.url.path)
    
    # Determine which service to route to
    service_url = get_service_url(full_path)
    
    if not service_url:
        raise HTTPException(
            status_code=404,
            detail={"error": "Not Found", "message": "Service not found for this path"}
        )
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Get headers, exclude the host header
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # Get the request method
    method = request.method
    
    # Get request body if it exists
    body = await request.body()
    
    try:
        async with httpx.AsyncClient() as client:
            # Make the request to the target service
            response = await client.request(
                method,
                f"{service_url}{full_path}",
                params=query_params,
                headers=headers,
                content=body,
                timeout=30.0
            )
            
            # Create a response with the same status code, headers, and content
            try:
                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.content else {}
                )
            except:
                # If not JSON, return the raw content
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to {service_url}{full_path}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Service Unavailable", "message": str(e)}
        )

# Create ASGI application for Gunicorn
# This is the entry point that Gunicorn will use
app = app