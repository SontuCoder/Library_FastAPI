from pydantic import BaseModel, EmailStr
from datetime import datetime

class SignUp(BaseModel):
    email:EmailStr
    password: str

class VerifyOTP(BaseModel):
    email:EmailStr
    otp:str

class Login(BaseModel):
    email:EmailStr
    password: str

# class AccessTokenModel(BaseModel):
#     email: EmailStr
#     type: str = "access"
#     exp: datetime
#     iat: datetime

# class RefreshTokenModel(BaseModel):
#     email: EmailStr
#     type: str = "refresh"
#     jti: str
#     exp: datetime
#     iat: datetime

# class JTISession(BaseModel):
#     email: EmailStr
#     created_at: datetime
#     expires_at: datetime