from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from redis import Redis
from app.db.session import get_db
from app.core.config import settings
from app.services.s3 import storage_service
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get("", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    health_status = {
        "postgres_postgis": "DOWN",
        "redis": "DOWN",
        "storage": "DOWN"
    }
    
    # 1. Check PostgreSQL & PostGIS
    try:
        result = db.execute(text("SELECT PostGIS_Version();")).scalar()
        if result:
            health_status["postgres_postgis"] = f"UP (PostGIS {result})"
    except Exception as e:
        health_status["postgres_postgis"] = f"ERROR: {str(e)}"

    # 2. Check Redis
    try:
        r = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=1)
        if r.ping():
            health_status["redis"] = "UP"
    except Exception as e:
        health_status["redis"] = f"ERROR: {str(e)}"

    # 3. Check Local Storage
    if storage_service.is_healthy():
        health_status["storage"] = "UP (Local Disk)"

    overall = "HEALTHY" if all("UP" in s for s in health_status.values()) else "UNHEALTHY"
    return HealthResponse(status=overall, services=health_status)