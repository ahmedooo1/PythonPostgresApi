from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from user_service.database import Base
import enum

class UserRole(str, enum.Enum):
    CLIENT = "client"
    PROVIDER = "prestataire"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, email={self.email}, role={self.role})"