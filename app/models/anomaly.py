import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from geoalchemy2 import Geometry
from app.db.session import Base

class AnomalyTrackModel(Base):
    __tablename__ = "anomalies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    anomaly_type = Column(String(32), nullable=False)  # CYCLONE, HEAT_DOME, COLD_WAVE
    valid_time = Column(DateTime, nullable=False)
    efi_score = Column(Float, nullable=False)
    
    # 4D Moving Envelopes represented as 2D spatial bounding polygon with time dimension
    bbox_geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)