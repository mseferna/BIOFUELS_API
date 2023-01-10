from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class Alarm(BaseModel):
    id: Optional[int] = 1
    probe_number: int
    product_name: str
    acknowledged: Optional[int]
    diff: float
    created: Optional[str]=now.strftime('%Y/%m/%d %H:%M:%S')
    comment: Optional[str]
    tank_id: Optional[int]
