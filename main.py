from flask import Flask, request, jsonify, Response, url_for
from flask_cors import CORS
import os
import logging
import requests
from typing import Dict, Any, Optional
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://localhost:8000", 
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
    "*"  # For development
]

# Add CORS middleware
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

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

@app.route('/')
def root():
    """Root endpoint with API information"""
    return jsonify({
        "message": "Service Platform API Gateway",
        "version": "1.0.0",
        "documentation": "/api-docs",
        "healthcheck": "/health"
    })

@app.route('/api-docs')
def api_docs():
    """API Documentation"""
    services = []
    for route, url in SERVICE_ROUTES.items():
        services.append({
            "name": route.replace("/api/", ""),
            "url": route,
            "health": f"{route}/health"
        })
    
    return jsonify({
        "api_name": "Service Platform API",
        "version": "1.0.0",
        "services": services,
        "endpoints": {
            "root": "/",
            "health": "/health",
            "api_docs": "/api-docs"
        }
    })

@app.route('/health')
def health_check():
    """Check the health of all services"""
    health_statuses = {}
    service_status = "healthy"  # Default status
    
    # Check health of all services
    for service_name, service_url in SERVICE_ROUTES.items():
        try:
            response = requests.get(f"{service_url}/health", timeout=2.0)
            if response.status_code == 200:
                health_statuses[service_name] = "healthy"
            else:
                health_statuses[service_name] = f"unhealthy (status: {response.status_code})"
                service_status = "degraded"
        except Exception as e:
            health_statuses[service_name] = f"unavailable ({str(e)})"
            service_status = "degraded"
    
    return jsonify({
        "status": service_status,
        "service": "api-gateway",
        "services": health_statuses
    })

@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
def proxy_endpoint(path):
    """Generic endpoint that proxies requests to the appropriate service"""
    # Get the full path
    full_path = request.path
    
    # Determine which service to route to
    service_url = get_service_url(full_path)
    
    if not service_url:
        return jsonify({
            "error": "Not Found", 
            "message": "Service not found for this path"
        }), 404
    
    # Forward the request to the target service
    target_url = f"{service_url}{full_path}"
    
    # Get the method, headers and query parameters
    method = request.method
    headers = {key: value for key, value in request.headers if key != 'Host'}
    params = request.args
    
    try:
        # Make the request to the target service
        if method == 'GET':
            response = requests.get(target_url, headers=headers, params=params, timeout=30.0)
        elif method == 'POST':
            response = requests.post(
                target_url, 
                headers=headers, 
                params=params, 
                json=request.json if request.is_json else None,
                data=request.form if not request.is_json else None,
                timeout=30.0
            )
        elif method == 'PUT':
            response = requests.put(
                target_url, 
                headers=headers, 
                params=params, 
                json=request.json if request.is_json else None,
                data=request.form if not request.is_json else None,
                timeout=30.0
            )
        elif method == 'DELETE':
            response = requests.delete(target_url, headers=headers, params=params, timeout=30.0)
        elif method == 'PATCH':
            response = requests.patch(
                target_url, 
                headers=headers, 
                params=params, 
                json=request.json if request.is_json else None,
                data=request.form if not request.is_json else None,
                timeout=30.0
            )
        else:
            # Handle other methods
            return jsonify({
                "error": "Method Not Allowed", 
                "message": f"Method {method} not supported"
            }), 405
        
        # Try to get JSON response, but handle non-JSON responses too
        try:
            response_data = response.json()
            return jsonify(response_data), response.status_code
        except ValueError:
            # Return raw response for non-JSON content
            return Response(
                response.content, 
                status=response.status_code, 
                content_type=response.headers.get('Content-Type', 'text/plain')
            )
            
    except requests.RequestException as e:
        logger.error(f"Error proxying request to {target_url}: {str(e)}")
        return jsonify({
            "error": "Service Unavailable", 
            "message": str(e)
        }), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)