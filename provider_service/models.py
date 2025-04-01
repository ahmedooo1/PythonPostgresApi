from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, func
from .database import Base

class Provider(Base):
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    availability = Column(Boolean, default=True)
    latitude = Column(Float(precision=9), nullable=False)
    longitude = Column(Float(precision=9), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"Provider(id={self.id}, name={self.name}, email={self.email}, availability={self.availability})"
