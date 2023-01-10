from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class Relay(BaseModel):
    #id: Optional[int] = 1
    host: str
    user: str
    password: str
    created: Optional[str]=now.strftime('%Y/%m/%d %H:%M:%S')