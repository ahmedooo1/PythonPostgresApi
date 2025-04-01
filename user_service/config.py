import os

# Service configuration
SERVICE_NAME = "user"
SERVICE_HOST = os.getenv("USER_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("USER_SERVICE_PORT", 8000))

# API prefix
API_PREFIX = "/api/users"
API_VERSION = "v1"

# Authentication settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-tokens")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:5000",  # Frontend
    "http://localhost:8000",  # API Gateway
    "http://0.0.0.0:5000",
    "http://0.0.0.0:8000",
]
