from pydantic import BaseModel, EmailStr

class SignUp(BaseModel):
    email:EmailStr
    password: str

class VerifyOTP(BaseModel):
    email:EmailStr
    otp:str

class Login(BaseModel):
    email:EmailStr
    password: str