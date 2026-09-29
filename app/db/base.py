# Import all models here so Alembic registers them on Base.metadata
from app.db.session import Base
from app.models.job import JobModel
from app.models.forecast import ForecastRunModel
from app.models.anomaly import AnomalyTrackModel
from app.models.alert import AlertZoneModel