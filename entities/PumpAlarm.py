from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class PumpAlarm(BaseModel):
    id: Optional[int] = 1
    pump_number: int
    code: Optional[int]
    product_name: Optional[str]
    acknowledged: Optional[int]
    created: Optional[str]=now.strftime('%Y/%m/%d %H:%M:%S')
    comment: Optional[str]