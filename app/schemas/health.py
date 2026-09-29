from typing import Dict
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]