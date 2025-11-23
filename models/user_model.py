from pydantic import BaseModel, EmailStr
from enum import Enum

class RoleEnum(str, Enum):
    student = "student"
    admin = "admin"


class User(BaseModel):
    name: str = ''
    email:EmailStr
    password:str
    role: RoleEnum = RoleEnum.student