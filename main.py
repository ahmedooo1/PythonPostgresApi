from flask import Flask, request, jsonify, Response 
from flask_cors import CORS
import os
import logging
import requests
from typing import Dict, Any, Optional, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a dedicated logger for failed service requests
failed_requests_logger = logging.getLogger("failed_requests")
failed_requests_handler = logging.FileHandler("failed_requests.log")
failed_requests_handler.setLevel(logging.ERROR)
failed_requests_logger.addHandler(failed_requests_handler)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Add CORS middleware
CORS(app, origins="*", supports_credentials=True)

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

def check_service_health_with_retries(service_url: str, retries: int = 3, timeout: float = 2.0) -> str:
    """Check the health of a service with retries."""
    for attempt in range(retries):
        try:
            response = requests.get(f"{service_url}/health", timeout=timeout)
            if response.status_code == 200:
                return "healthy"
            else:
                return f"unhealthy (status: {response.status_code})"
        except requests.RequestException as e:
            if attempt < retries - 1:
                continue  # Retry
            return f"unavailable ({str(e)})"

@app.route('/health')
def health_check():
    """Check the health of all services"""
    health_statuses = {}
    service_status = "healthy"  # Default status
    
    # Check health of all services with retries
    for service_name, service_url in SERVICE_ROUTES.items():
        status = check_service_health_with_retries(service_url)
        health_statuses[service_name] = status
        if "unhealthy" in status or "unavailable" in status:
            service_status = "degraded"
    
    return jsonify({
        "status": service_status,
        "service": "api-gateway",
        "services": health_statuses
    })

@app.route('/service-health', methods=["GET"])
def service_health():
    """Check the connectivity of individual services"""
    service_health_status = {}
    
    # Check health of all services with retries
    for service_name, service_url in SERVICE_ROUTES.items():
        service_health_status[service_name] = check_service_health_with_retries(service_url)
    
    return jsonify({
        "status": "ok",
        "services": service_health_status
    })

@app.route('/fallback/<service_name>', methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
def fallback_service(service_name):
    """Fallback response for unavailable services."""
    return jsonify({
        "error": "Service Unavailable",
        "message": f"The {service_name} service is currently unavailable.",
        "suggestions": [
            f"Ensure the {service_name} service is running and accessible.",
            "Check the service logs for potential issues.",
            "Verify the service configuration and network settings."
        ]
    }), 503

# Notify administrators or log critical errors for unavailable services
def notify_critical_error(service_name: str, service_url: str, error: str):
    """Log critical errors or notify administrators."""
    critical_message = f"CRITICAL: Service {service_name} at {service_url} is consistently unavailable. Error: {error}"
    logger.critical(critical_message)
    # Placeholder for notification logic (e.g., email, Slack, etc.)
    # send_notification_to_admins(critical_message)

# Track consecutive failures for each service
service_failure_counts = {}

def track_service_failure(service_name: str, service_url: str, error: str, threshold: int = 3):
    """Track consecutive failures for a service and log a warning if the threshold is exceeded."""
    if service_name not in service_failure_counts:
        service_failure_counts[service_name] = 0
    service_failure_counts[service_name] += 1

    if service_failure_counts[service_name] >= threshold:
        logger.warning(f"Service {service_name} at {service_url} has failed {service_failure_counts[service_name]} times consecutively. Error: {error}")
        # Reset the failure count after logging the warning
        service_failure_counts[service_name] = 0

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
    service_name = full_path.split('/')[2] if len(full_path.split('/')) > 2 else "unknown"

    try:
        # Get the method, headers and query parameters
        method = request.method
        headers = {key: value for key, value in request.headers if key != 'Host'}
        params = request.args
        
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
        failed_requests_logger.error({
            "service_url": service_url,
            "requested_path": full_path,
            "error": str(e)
        })
        # Track service failure
        track_service_failure(service_name, service_url, str(e))
        # Notify critical error if service is consistently unavailable
        notify_critical_error(service_name, service_url, str(e))
        # Redirect to fallback endpoint
        return fallback_service(service_name)

def check_services_on_startup():
    """Check the availability of all services during startup."""
    logger.info("Performing startup service availability check...")
    for service_name, service_url in SERVICE_ROUTES.items():
        status = check_service_health_with_retries(service_url, retries=1, timeout=2.0)
        if "unavailable" in status or "unhealthy" in status:
            logger.warning(f"Service {service_name} at {service_url} is {status}.")
        else:
            logger.info(f"Service {service_name} at {service_url} is {status}.")

if __name__ == "__main__":
    check_services_on_startup()
    app.run(host="0.0.0.0", port=5000, debug=True)