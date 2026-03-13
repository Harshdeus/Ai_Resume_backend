from sqlalchemy import Column, Integer, String, DateTime, Text
from database.models.db import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    years_of_experience = Column(String(100), nullable=True)

    jd = Column(Text, nullable=True)

    active_till_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=True)

    created_time = Column(DateTime, nullable=True)
    updated_time = Column(DateTime, nullable=True)

    # multi-user support
    user_id = Column(Integer, nullable=True)

    # new fields
    work_mode = Column(String(100), nullable=True)
    employment_type = Column(String(100), nullable=True)
    min_budget_lpa = Column(String(50), nullable=True)
    max_budget_lpa = Column(String(50), nullable=True)