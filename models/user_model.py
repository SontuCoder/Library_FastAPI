from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional


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
    password: Optional[str] = None   # NULL for social login
    role: RoleEnum = RoleEnum.student
    provider: Provider = Provider.local
    provider_id: Optional[str] = None