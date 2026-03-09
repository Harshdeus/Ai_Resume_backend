from sqlalchemy import Column, Integer, String, DateTime, Text
from database.models.db import Base
from datetime import datetime

class JobDescription(Base):
    __tablename__ = "job_descriptions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    years_of_experience = Column(String(50), nullable=False)
    jd = Column(Text, nullable=True)
    active_till_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    created_time = Column(DateTime, default=datetime.now(), nullable=False)
    updated_time = Column(DateTime, nullable=True)