from pydantic import BaseModel
from typing import Optional
from datetime import datetime

now = datetime.now()

class SOLogin(BaseModel):
    user: str 
    password: str
