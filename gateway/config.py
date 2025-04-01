import os

# Service configuration
SERVICE_NAME = "gateway"
SERVICE_HOST = os.getenv("GATEWAY_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("GATEWAY_SERVICE_PORT", 5000))

# API prefix
API_PREFIX = "/api"

# Service URLs
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8000")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment_service:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification_service:8000")
PROVIDER_SERVICE_URL = os.getenv("PROVIDER_SERVICE_URL", "http://provider_service:8000")
REPAIR_SERVICE_URL = os.getenv("REPAIR_SERVICE_URL", "http://repair_service:8000")
CHILD_ASSISTANCE_SERVICE_URL = os.getenv("CHILD_ASSISTANCE_SERVICE_URL", "http://child_assistance_service:8000")
MOVING_SERVICE_URL = os.getenv("MOVING_SERVICE_URL", "http://moving_service:8000")
CLEANING_SERVICE_URL = os.getenv("CLEANING_SERVICE_URL", "http://cleaning_service:8000")

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:5000",  # Frontend
    "http://localhost:8000",  # API Gateway
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
    "*"  # For development
]
