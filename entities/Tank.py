from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class Tank(BaseModel):
    id: Optional[int]
    number: int
    product_name: str
    probe_number: int
    capacity: float
    threshold: float
    monitoring: Optional[int] = 0
    #action: str
    created: Optional[str]=now.strftime('%Y/%m/%d %H:%M:%S')