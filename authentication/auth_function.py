from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from passlib.context import CryptContext
import traceback
import time 


from db_connection.db_provider import get_db
from models.auth_model import SignUp, VerifyOTP
from models.user_model import User
from authentication.send_mail import generate_otp, send_mail_fast
from db_connection.redis_function import save_data_redis, verify_otp_redis, get_saved_password, delete_data

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



@router.post("/signup")
async def signup(data: SignUp, backgound_task:BackgroundTasks, db = Depends(get_db)):
    try:
        if not data.email or not data.password:
            raise HTTPException(status_code=422,detail="Email and password are required.")

        user = await db.users.find_one({"email": data.email})
        if user:
            raise HTTPException(status_code=400,detail="User already exists.")
        
        otp = generate_otp()
        hash_pass = hash_password(data.password)
        username, domain = data.email.split("@")
        mail= "".join([username[:5], "***@", domain])
        backgound_task.add_task(save_data_redis, data.email, otp, 'otp')
        backgound_task.add_task(save_data_redis, data.email, hash_pass, 'password')
        backgound_task.add_task(send_mail_fast, data.email, otp)

        return { "status": "success", "message" : f"OTP mail send successfully in {mail}" }
    

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    

@router.post("/verify-otp")
async def verify_otp(data:VerifyOTP, backgound_task:BackgroundTasks, db = Depends(get_db)):
    try:
        if not data.email or not data.otp:
            raise HTTPException(status_code=422,detail="Email and OTP are required.")
        is_verify = verify_otp_redis(data.email, data.otp)
        if not is_verify:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        password = get_saved_password(data.email)
        if not password:
            raise HTTPException(status_code=400,detail="Password expired or missing")
        
        new_user = User(
            email=data.email,
            password=password
        )
        backgound_task.add_task(delete_data, data.email, 'otp')
        backgound_task.add_task(delete_data, data.email, 'password')
        await db.users.insert_one(new_user.model_dump())
        return { "status": "success", "message" : "OTP verify successfully" }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

