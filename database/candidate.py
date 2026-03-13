from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database.models.db import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String(255))
    experience = Column(String(255))
    score = Column(Float)
    extracted_on = Column(DateTime)
    position = Column(String(255))

    # ✅ ADD THIS LINE
    user_id = Column(Integer, ForeignKey("users.id"))