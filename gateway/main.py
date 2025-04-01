from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from .config import SERVICE_HOST, SERVICE_PORT, ALLOWED_ORIGINS
from .routers import router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Service Platform API Gateway",
    description="API Gateway for the Service Platform microservices",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Service Platform API Gateway",
        "version": "1.0.0",
        "documentation": "/docs",
        "healthcheck": "/health"
    }

if __name__ == "__main__":
    logger.info(f"Starting API Gateway on {SERVICE_HOST}:{SERVICE_PORT}")
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
