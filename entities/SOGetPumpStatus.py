from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SOGetPumpStatus(BaseModel):
    session_id: str 
    pump_number: int
