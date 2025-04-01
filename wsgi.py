import uvicorn
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from main import app

# Wrap the FastAPI app with WSGI middleware to make it compatible with Gunicorn
wsgi_app = WSGIMiddleware(app)

# This is the entry point for Gunicorn
application = wsgi_app

# For local development
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)