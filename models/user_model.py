from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional
from datetime import datetime


class RoleEnum(str, Enum):
    student = "student"
    admin = "admin"

class Provider(str, Enum):
    google = 'google'
    github = 'github'
    local = 'local'


class User(BaseModel):
    name: Optional[str] = None 
    email:EmailStr
    password: Optional[str] = None
    role: RoleEnum = RoleEnum.student
    provider: Provider = Provider.local
    provider_id: Optional[str] = None
    created_at: datetime = datetime.utcnow()

class Profile_Update(BaseModel):
    name: Optional[str] = None 