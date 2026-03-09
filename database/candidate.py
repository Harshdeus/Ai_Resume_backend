from sqlalchemy import Column, Integer, String, Float, DateTime
from database.models.db import Base
from datetime import datetime

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String(255), nullable=False)
    position = Column(String(255), nullable=True)
    experience = Column(String(100), nullable=True)
    score = Column(Float, nullable=True)

    # ✅ Match DB column name exactly
    extracted_on = Column(DateTime, default=datetime.now, nullable=False)