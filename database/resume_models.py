from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from database.models.db import Base
from datetime import datetime

class ResumeUpload(Base):
    __tablename__ = "resume_uploads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    filename = Column(String(255))
    output_resume = Column(String(255))
    score = Column(Float)
    email = Column(String(200))
    Time = Column(DateTime, default=datetime.now)
    score2 = Column(Float)
    missing_info = Column(String(255))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)