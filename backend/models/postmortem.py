from pydantic import BaseModel
from typing import Optional


class Postmortem(BaseModel):
    incident_id: str
    root_cause: str
    resolution: str
    outcome: str
    recovery_time: Optional[str] = None
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None