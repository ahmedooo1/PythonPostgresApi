from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Function to create SQLAlchemy database connection URL from environment variables
def get_database_url(service_name):
    """Create database URL from environment variables with a service-specific database name"""
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "postgres")
    
    # Use the provided service name as the database name suffix
    database = f"{os.getenv('PGDATABASE', 'service_db')}_{service_name}"
    
    # If full DATABASE_URL is provided, use that instead
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Function to create database engine and session
def setup_database(service_name):
    """Set up SQLAlchemy engine and session for a specific service"""
    database_url = get_database_url(service_name)
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    return engine, SessionLocal, Base

# Database dependency
def get_db(db_session):
    """Database session dependency to be used in FastAPI endpoints"""
    db = db_session()
    try:
        yield db
    finally:
        db.close()
