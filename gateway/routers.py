from fastapi import APIRouter, Request, Response, HTTPException
import httpx
from httpx import AsyncClient, RequestError
from starlette.background import BackgroundTask
import logging
from typing import Dict, Any

from .config import (
    USER_SERVICE_URL,
    ORDER_SERVICE_URL,
    PAYMENT_SERVICE_URL,
    NOTIFICATION_SERVICE_URL,
    PROVIDER_SERVICE_URL,
    REPAIR_SERVICE_URL,
    CHILD_ASSISTANCE_SERVICE_URL,
    MOVING_SERVICE_URL,
    CLEANING_SERVICE_URL,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Create router
router = APIRouter()


def get_service_url(path: str) -> str:
    """Determine which service to route to based on the path"""
    for route_prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(route_prefix):
            return service_url
    return None


async def proxy_request(request: Request, service_url: str) -> Response:
    """Proxy the request to the appropriate service"""
    # Get the path that should be appended to the service URL
    path = request.url.path
    
    # Get the target URL
    target_url = f"{service_url}{path}"
    
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
        async with AsyncClient() as client:
            # Make the request to the target service
            response = await client.request(
                method,
                target_url,
                params=query_params,
                headers=headers,
                content=body,
                timeout=30.0
            )
            
            # Create a response with the same status code, headers, and content
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                background=BackgroundTask(response.aclose)
            )
    except RequestError as e:
        logger.error(f"Error proxying request to {target_url}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_endpoint(request: Request, path: str):
    """Generic endpoint that proxies requests to the appropriate service"""
    # Get the full path
    full_path = request.url.path
    
    # Determine which service to route to
    service_url = get_service_url(full_path)
    
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found for this path")
    
    # Proxy the request to the service
    return await proxy_request(request, service_url)


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check the health of all services"""
    health_statuses = {}
    
    async with AsyncClient() as client:
        for service_name, service_url in SERVICE_ROUTES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                if response.status_code == 200:
                    health_statuses[service_name] = "healthy"
                else:
                    health_statuses[service_name] = f"unhealthy (status: {response.status_code})"
            except Exception as e:
                health_statuses[service_name] = f"unavailable ({str(e)})"
    
    return {
        "status": "healthy",
        "service": "api-gateway",
        "services": health_statuses
    }
