import os

# Service configuration
SERVICE_NAME = "gateway"
SERVICE_HOST = os.getenv("GATEWAY_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("GATEWAY_SERVICE_PORT", 5000))

# API prefix
API_PREFIX = "/api"

# Service URLs
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://0.0.0.0:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://0.0.0.0:8001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://0.0.0.0:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://0.0.0.0:8003")
PROVIDER_SERVICE_URL = os.getenv("PROVIDER_SERVICE_URL", "http://0.0.0.0:8004")
REPAIR_SERVICE_URL = os.getenv("REPAIR_SERVICE_URL", "http://0.0.0.0:8005")
CHILD_ASSISTANCE_SERVICE_URL = os.getenv("CHILD_ASSISTANCE_SERVICE_URL", "http://0.0.0.0:8006")
MOVING_SERVICE_URL = os.getenv("MOVING_SERVICE_URL", "http://0.0.0.0:8007")
CLEANING_SERVICE_URL = os.getenv("CLEANING_SERVICE_URL", "http://0.0.0.0:8008")

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:5000",  # Frontend
    "http://localhost:8000",  # API Gateway
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
    "*"  # For development
]