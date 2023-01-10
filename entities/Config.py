from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class Config(BaseModel):
    id: Optional[int] = 1
    host: str
    port: int
    depositoId: int
    created: Optional[str]=now.strftime('%Y/%m/%d %H:%M:%S')
