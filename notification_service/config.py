import os

# Service configuration
SERVICE_NAME = "notification"
SERVICE_HOST = os.getenv("NOTIFICATION_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("NOTIFICATION_SERVICE_PORT", 8000))

# API prefix
API_PREFIX = "/api/notifications"
API_VERSION = "v1"

# User service configuration for authentication
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:5000",  # Frontend
    "http://localhost:8000",  # API Gateway
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
]
