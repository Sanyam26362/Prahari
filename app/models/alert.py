import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from geoalchemy2 import Geometry
from app.db.session import Base
import enum

class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"

class AlertZoneModel(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_id = Column(String, ForeignKey("anomalies.id"), nullable=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    peak_metric_value = Column(Float, nullable=False)   # e.g., max wind speed (km/h) or mm rain
    metric_unit = Column(String(16), nullable=False)    # km/h, C, mm
    
    # Precise localized pin-point and 5 km impact area
    center_point = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    impact_zone_5km = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)