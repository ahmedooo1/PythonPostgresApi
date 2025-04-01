
import os

# Gateway Service Configuration
SERVICE_HOST = os.getenv("GATEWAY_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("GATEWAY_SERVICE_PORT", 5000))

# Microservices URLs
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://0.0.0.0:8000")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://0.0.0.0:8001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://0.0.0.0:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://0.0.0.0:8003")
PROVIDER_SERVICE_URL = os.getenv("PROVIDER_SERVICE_URL", "http://0.0.0.0:8004")
REPAIR_SERVICE_URL = os.getenv("REPAIR_SERVICE_URL", "http://0.0.0.0:8005")
CHILD_ASSISTANCE_SERVICE_URL = os.getenv("CHILD_ASSISTANCE_SERVICE_URL", "http://0.0.0.0:8006")
MOVING_SERVICE_URL = os.getenv("MOVING_SERVICE_URL", "http://0.0.0.0:8007")
CLEANING_SERVICE_URL = os.getenv("CLEANING_SERVICE_URL", "http://0.0.0.0:8008")

# API Configuration
API_PREFIX = "/api"
API_VERSION = "v1"

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
    "http://0.0.0.0:8001",
    "http://0.0.0.0:8002", 
    "http://0.0.0.0:8003",
    "http://0.0.0.0:8004",
    "http://0.0.0.0:8005",
    "http://0.0.0.0:8006",
    "http://0.0.0.0:8007",
    "http://0.0.0.0:8008"
]
