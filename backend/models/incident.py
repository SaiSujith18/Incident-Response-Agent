from pydantic import BaseModel
from typing import Optional


class ResolutionRequest(BaseModel):
    incident_id: str
    resolution: str
    outcome: str
    recovery_time: Optional[str] = None
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None