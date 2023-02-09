from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class SOSimple(BaseModel):
    session_id: str 
    site_code: str
    so_url: str
