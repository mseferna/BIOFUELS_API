from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class Inventory(BaseModel):
    #id: Optional[int] = 1
    host: str
    req_type: str
    date: str
    time: str
    probe_number: int
    volume: float
    tc_volume: float
    ullage: float
    height: float
    water: float
    temp: float
    delivery_in_progress: int
    depositoId: int
    product_name: str