from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database.models.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(255), default="candidate")
    is_logged_in = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now())
    last_login = Column(DateTime, default=None)