import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text
from app.db.session import Base
import enum

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    GNN_PROCESSING = "GNN_PROCESSING"
    DIFFUSION_PROCESSING = "DIFFUSION_PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    stage = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)