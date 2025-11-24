from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import traceback


from db_connection.db_provider import get_db
from models.auth_model import SignUp, VerifyOTP, Login
from models.user_model import User
from authentication.send_mail import generate_otp, send_mail_fast
from db_connection.redis_function import save_data_redis, verify_otp_redis, get_saved_password, delete_data
from utility.jwt_helper import create_access_token, create_refresh_token, verify_access_token, verify_refresh_token
from utility.jti_helper import generate_jti, save_jti, create_session, validate_jti, rotate_jti, get_jti_session, delete_jti

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



@router.post("/signup")
async def signup(data: SignUp, background_task:BackgroundTasks, db = Depends(get_db)):
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
        background_task.add_task(save_data_redis, data.email, otp, 'otp')
        background_task.add_task(save_data_redis, data.email, hash_pass, 'password')
        background_task.add_task(send_mail_fast, data.email, otp)

        print(otp, data.email)
        return { "status": "success", "message" : f"OTP mail send successfully in {mail}"}
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    

@router.post("/verify-otp")
async def verify_otp(data:VerifyOTP, response: Response, background_task:BackgroundTasks, db = Depends(get_db)):
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
        await db.users.insert_one(new_user.model_dump())
        background_task.add_task(delete_data, data.email, 'otp')
        background_task.add_task(delete_data, data.email, 'password')

        jti = generate_jti()              
        session = create_session(data.email, new_user.role)     
        save_jti(jti, session)

        access_token = create_access_token(data.email, new_user.role)
        refresh_token = create_refresh_token(data.email, jti)
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 15,
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 60 * 24 * 30,
        )

        return { "status": "success", "message" : "OTP verify successfully" }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")


@router.post("/login")
async def login(data:Login, response: Response, db = Depends(get_db)):
    try:
        if not data.email or not data.password:
            raise HTTPException(status_code=422,detail="Email and Password are required.")
        
        user = await db.users.find_one({"email": data.email})
        if not user:
            raise HTTPException(status_code=400,detail="User not exists.")
        
        if not verify_password(data.password, user["password"]):
            raise HTTPException(status_code=400,detail="Wrong Password")
        
        role = user.get("role", "student")
        jti = generate_jti()              
        session = create_session(data.email, role)     
        save_jti(jti, session)

        access_token = create_access_token(data.email, role)
        refresh_token = create_refresh_token(data.email, jti)
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 15
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 60 * 24 * 30
        )

        return { "status": "success", "message" : "Login successfully" }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")


@router.post("/refresh-token")
async def refresh_token(request: Request, response: Response):
    
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="refresh_token_missing")

    try:
        payload = verify_refresh_token(refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    email = payload.get("email")
    old_jti = payload.get("jti")
    if not email or not old_jti:
        raise HTTPException(status_code=401, detail="invalid_refresh_token_payload")

    if not validate_jti(old_jti, email):
        raise HTTPException(status_code=401, detail="refresh_token_revoked_or_invalid")
    
    
    try:
        session = get_jti_session(old_jti)
        role = session["role"]
        new_jti = rotate_jti(old_jti)
    except Exception:
        raise

    new_access = create_access_token(email, role)
    new_refresh = create_refresh_token(email, new_jti)

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=new_access,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 15,
    )

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 60 * 60,
    )

    return {"status": "success", "message": "tokens_rotated"}

@router.post("/logout")
async def logout(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            payload = verify_refresh_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                delete_jti(jti)
        except Exception:
            # If token invalid/expired we still clear cookies
            pass

    # Clear cookies on response (set empty + max_age=0)
    response.delete_cookie(ACCESS_COOKIE_NAME)
    response.delete_cookie(REFRESH_COOKIE_NAME)
    return {"status": "success", "message": "logged_out"}


async def get_current_user(request: Request,credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    token = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        token = request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401, detail="access_token_missing")

    try:
        payload = verify_access_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    email = payload.get("email")    
    role = payload.get("role")    
    if not email or not role:
        raise HTTPException(status_code=401, detail="invalid_access_token_payload")
    
    return payload


@router.get("/dashboard")
async def dashboard(user = Depends(get_current_user)):
    return {"message": "Welcome", "email": user['email'], "role":user['role']}