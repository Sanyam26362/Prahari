import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float
from app.db.session import Base

class ForecastRunModel(Base):
    __tablename__ = "forecast_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(32), nullable=False)  # NCUM_12KM, NEPS_G
    run_date = Column(DateTime, nullable=False)
    forecast_horizon_hours = Column(Float, nullable=False)  # e.g., 240.0 (10 days)
    storage_path = Column(String(512), nullable=False)      # MinIO S3 URI
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)