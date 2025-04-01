import sys
import os

# Add the parent directory to sys.path to import from shared package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database_utils import setup_database
from .config import SERVICE_NAME

# Set up database connection
engine, SessionLocal, Base = setup_database(SERVICE_NAME)

# Database dependency to be used in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
